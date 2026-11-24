from io import BytesIO
from .marketplaces import marketplace_for
from zipfile import ZipFile

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill

HEADERS = ("Ссылка на товар", "Интервал, мин")
MAX_BYTES = 512 * 1024


def template():
    book = Workbook()
    sheet = book.active
    sheet.title = "Отслеживания"
    sheet.append(HEADERS)
    for cell in sheet[1]:
        cell.fill = PatternFill("solid", fgColor="244469")
        cell.font = Font(bold=True, color="FFFFFF")
    sheet.column_dimensions["A"].width = 75
    sheet.column_dimensions["B"].width = 20
    sheet.freeze_panes = "A2"
    output = BytesIO()
    book.save(output)
    return output.getvalue()


def parse_sheet(data):
    if len(data) > MAX_BYTES:
        raise ValueError("Максимальный размер файла — 512 КБ")
    try:
        with ZipFile(BytesIO(data)) as archive:
            if sum(item.file_size for item in archive.infolist()) > 4 * 1024 * 1024:
                raise ValueError
        book = load_workbook(BytesIO(data), read_only=True)
        try:
            sheet = book.worksheets[0]
            sheet.reset_dimensions()
            rows = []
            for row in sheet.iter_rows(max_col=2, values_only=True):
                if len(rows) >= 501:
                    raise OverflowError
                rows.append(row)
        finally:
            book.close()
    except OverflowError as exc:
        raise ValueError("В файле допускается до 500 строк данных") from exc
    except Exception as exc:
        raise ValueError("Не удалось прочитать файл .xlsx") from exc
    if not rows or rows[0] not in (HEADERS, ("Ссылка Ozon", HEADERS[1])):
        raise ValueError("Заголовки должны совпадать с шаблоном")
    orders = {}
    for number, (url, interval) in enumerate(rows[1:], 2):
        if url is None and interval is None:
            continue
        url = url.strip() if isinstance(url, str) else ""
        try:
            marketplace_for(url)
        except ValueError as exc:
            raise ValueError(f"Строка {number}: {exc}") from exc
        interval = 60 if interval is None else interval
        if interval not in (60, 360, 1440):
            raise ValueError(f"Строка {number}: допустимые интервалы — 60, 360 и 1440 минут")
        if url in orders and orders[url] != interval:
            raise ValueError(f"Строка {number}: ссылка повторяется с другим интервалом")
        orders[url] = int(interval)
    if not orders:
        raise ValueError("Добавьте хотя бы одну ссылку в файл")
    return orders
