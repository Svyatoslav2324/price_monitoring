"""PostgreSQL-backed scheduler and parser worker. Run via python -m app.queue."""
import argparse
import asyncio
import logging
import time
from decimal import Decimal
from importlib import import_module
from uuid import uuid4

from sqlalchemy import text

from .database import engine
from .price_status import UnavailablePrice


def enqueue_due():
    with engine.begin() as db:
        return db.execute(text("""
            WITH due AS (
                SELECT l.id, (
                    SELECT min(s.interval) FROM group_links g
                    JOIN subscriptions s ON s.group_id = g.group_id
                    WHERE g.link_id = l.id AND s.status = 'active'
                ) AS minutes
                FROM links l
                WHERE l.next_parse_at <= now()
                  AND EXISTS (SELECT 1 FROM group_links g JOIN subscriptions s
                      ON s.group_id = g.group_id WHERE g.link_id = l.id AND s.status = 'active')
                  AND NOT EXISTS (SELECT 1 FROM parse_jobs j WHERE j.link_id = l.id)
                ORDER BY l.next_parse_at, l.id LIMIT 100 FOR UPDATE OF l SKIP LOCKED
            ), queued AS (
                INSERT INTO parse_jobs (link_id) SELECT id FROM due
                ON CONFLICT DO NOTHING RETURNING link_id
            )
            UPDATE links l SET next_parse_at = now() + make_interval(mins => greatest(d.minutes, 1)),
                parse_interval = greatest(d.minutes, 1)
            FROM due d JOIN queued q ON q.link_id = d.id WHERE l.id = d.id
        """)).rowcount


def claim(marketplace=None):
    with engine.begin() as db:
        return db.execute(text("""
            WITH candidate AS (
                SELECT j.link_id FROM parse_jobs j
                JOIN links source ON source.id = j.link_id
                LEFT JOIN marketplaces m ON m.id = source.marketplace_id
                WHERE j.available_at <= now()
                  AND (CAST(:marketplace AS text) IS NULL OR m.name = :marketplace)
                ORDER BY j.available_at, j.link_id LIMIT 1 FOR UPDATE OF j SKIP LOCKED
            )
            UPDATE parse_jobs j SET token = :token, available_at = now() + interval '5 minutes'
            FROM candidate c JOIN links l ON l.id = c.link_id
            WHERE j.link_id = c.link_id RETURNING j.link_id, j.token, l.url, l.marketplace_id
        """), {"token": str(uuid4()), "marketplace": marketplace}).mappings().first()


def finish(job, price):
    with engine.begin() as db:
        removed = db.execute(text("""
            DELETE FROM parse_jobs WHERE link_id = :link_id AND token = :token
              AND available_at > clock_timestamp()
        """), dict(job))
        if removed.rowcount:
            unavailable = isinstance(price, UnavailablePrice)
            params = {"link_id": job["link_id"], "price": None if unavailable else price,
                      "status": price.value if unavailable else "available"}
            db.execute(text("""
                UPDATE links SET current_price = :price, price_status = :status, last_parsed_at = now() WHERE id = :link_id
            """), params)
            if unavailable:
                return
            db.execute(text("""
                INSERT INTO price_history (link_id, price) VALUES (:link_id, :price)
            """), params)


def retry(job):
    with engine.begin() as db:
        updated = db.execute(text("""
            UPDATE parse_jobs SET token = NULL, available_at = now() + interval '1 minute'
            WHERE link_id = :link_id AND token = :token AND available_at > clock_timestamp()
        """), dict(job))
        if updated.rowcount:
            db.execute(text("UPDATE links SET price_status = 'check_error' WHERE id = :link_id"), dict(job))


async def run_worker(parser, marketplace):
    while True:
        try:
            job = await asyncio.to_thread(claim, marketplace)
            if job is None:
                await asyncio.sleep(2)
                continue
            try:
                logging.info("Проверяю ссылку %s", job["link_id"])
                value = await parser(job["url"], job["marketplace_id"])
                if not isinstance(value, UnavailablePrice):
                    value = Decimal(str(value))
                    if not value.is_finite() or value < 0:
                        raise ValueError("Invalid price")
                await asyncio.to_thread(finish, job, value)
            except Exception:
                logging.exception("Price check failed for link %s", job["link_id"])
                await asyncio.to_thread(retry, job)
        except Exception:
            logging.exception("Queue database operation failed")
            await asyncio.sleep(2)


async def run_ozon(*, headed=False):
    import signal
    from .ozon import worker_session
    loop = asyncio.get_running_loop()
    loop.add_signal_handler(signal.SIGTERM, asyncio.current_task().cancel)
    try:
        async with worker_session(headed=headed) as parser:
            await run_worker(parser, "Ozon")
    except asyncio.CancelledError:
        pass
    finally:
        loop.remove_signal_handler(signal.SIGTERM)



def main():
    cli = argparse.ArgumentParser()
    modes = cli.add_subparsers(dest="mode", required=True)
    modes.add_parser("scheduler")
    worker = modes.add_parser("worker")
    worker.add_argument("--marketplace", help="Name from marketplaces.name")
    worker.add_argument("parser", help="module:function")
    ozon = modes.add_parser("ozon-worker")
    ozon.add_argument("--headed", action="store_true", help="Show browser window and progress logs")
    args = cli.parse_args()
    if args.mode == "ozon-worker":
        if args.headed:
            logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
        asyncio.run(run_ozon(headed=args.headed))
    elif args.mode == "worker":
        module, name = args.parser.split(":", 1)
        parser = getattr(import_module(module), name)

        async def parse(url, marketplace_id):
            return await asyncio.to_thread(parser, url, marketplace_id)

        asyncio.run(run_worker(parse, args.marketplace))
    else:
        while True:
            try:
                if enqueue_due():
                    continue
            except Exception:
                logging.exception("Queue database operation failed")
            time.sleep(2)


if __name__ == "__main__":
    main()
