from django.core.management.base import BaseCommand
from modules.tracking import worker


class Command(BaseCommand):
    help = "Фоновая проверка цен отслеживаемых товаров"

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true", help="Одна итерация и выход (для cron)")

    def handle(self, *args, once=False, **options):
        if once:
            self.stdout.write(f"checked: {worker.run_once()}")
        else:
            worker.run_forever()
