"""Exclusive leases on a fixed set of local Firefox profile directories."""
import asyncio
import fcntl
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path


@asynccontextmanager
async def lease_profile():
    root = Path(os.environ.get("OZON_PROFILE_DIR", "ozon-profiles"))
    size = int(os.environ.get("OZON_PROFILE_COUNT", "1"))
    pin = os.environ.get("OZON_PROFILE_SLOT")
    if size < 1 or (pin and not 1 <= int(pin) <= size):
        raise ValueError("Проверьте OZON_PROFILE_COUNT и OZON_PROFILE_SLOT")
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    slots = [int(pin)] if pin else range(1, size + 1)
    waiting = False
    while True:
        for slot in slots:
            with (root / f".slot-{slot}.lock").open("a") as lock:
                try:
                    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    continue
                path = root / f"slot-{slot}"
                path.mkdir(mode=0o700, exist_ok=True)
                logging.getLogger(__name__).warning("Ozon worker using profile %s", path.name)
                yield path
                return
        if not waiting:
            logging.getLogger(__name__).warning("Waiting for a free Ozon profile")
            waiting = True
        await asyncio.sleep(2)
