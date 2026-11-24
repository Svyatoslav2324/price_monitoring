"""Асинхронный парсер карточек из проекта uparser."""
import asyncio
import logging
import re
from pathlib import Path

from camoufox import AsyncCamoufox
from playwright.async_api import TimeoutError as PlaywrightTimeoutError


async def block_unnecessary(route):
    """
    if route.request.resource_type == "document":
        await route.continue_()
    else:
        await route.abort()
    """
    request = route.request

    if request.resource_type in ["image"]:
        await route.abort()
    else:
        await route.continue_()

def is_url(url):
    if url.startswith("http"):
        return True
    return False



async def wait_for_any(page, selectors, timeout=40000):
    # Каждый ожидатель привязан к селектору. Все оставшиеся задачи
    # отменяются и дожидаются завершения, чтобы не оставлять фоновые ожидания.
    tasks = {
        asyncio.create_task(page.wait_for_selector(selector, timeout=timeout)): selector
        for selector in selectors
    }
    pending = set(tasks)

    try:
        while pending:
            done, pending = await asyncio.wait(
                pending,
                return_when=asyncio.FIRST_COMPLETED,
            )

            for task in done:
                try:
                    await task
                    return tasks[task]
                except asyncio.CancelledError:
                    raise
                except Exception:
                    # Один селектор мог завершиться ошибкой; проверяем остальные.
                    continue

        return None
    finally:
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


class Parser:
    def __init__(self, name, parser_id=0, region="", *, profile_path=None, headed=False):
        self._id = parser_id
        self.region = region
        self.logger = logging.getLogger(name)
        self.headed = headed
        self.authentication = True

        self.browser = None
        self.context = None
        # Храним менеджер Camoufox, чтобы при остановке закрывать не только
        # контекст браузера, но и Playwright driver/соединение.
        self._camoufox = None

        self.products = []
        self.product_index = 0

        self.profile_path = str(profile_path or Path("ozon-profiles") / region / f"ozon_profile_{parser_id}")

    def _browser_manager(self, *, headed):
        return AsyncCamoufox(
            headless=not headed,
            geoip=True,
            humanize=True,
            os="windows",
            locale="ru-RU",
            persistent_context=True,
            user_data_dir=self.profile_path,
            #block_images=True,
            # Дополнительные настройки uparser отключены:
            # geoip, humanize, os, locale, block_images.
        )

    async def manual_login(self):
        self.logger.info("starting authorization...")

        camoufox = self._browser_manager(headed=True)
        started = False

        try:
            context = await camoufox.__aenter__()
            started = True
            page = await context.new_page()

            self.logger.info("press 'enter' after authorization")

            try:
                await page.goto(
                    "https://www.ozon.ru/login/",
                    wait_until="domcontentloaded",
                    timeout=40000,
                )
            except (TimeoutError, PlaywrightTimeoutError):
                self.logger.error("страница не загрузилась за отведенное время")
            except Exception as e:
                self.logger.error(f"error while trying to open page: {e}")
                return

            input()
            self.logger.info(f"authorization profile saved in {self.profile_path}")
        finally:
            if started:
                # AsyncCamoufox.__aexit__ закрывает браузер и Playwright driver.
                await camoufox.__aexit__(None, None, None)

    async def parse(self, url):
        if not(is_url(url)):
            self.logger.info(f"invalid url:{url}")
            if url == "":
                self.products.append({
                    "title": "",
                    "url": url,
                    "price": ""})
            else:
                self.products.append({
                    "title": "",
                    "url": url,
                    "price": "некорректная ссылка"})

            self.product_index += 1
            return self.products[self.product_index-1]

        self.logger.info(f"Parsing product {self.product_index}: {url}")

        for attempt in range(3):
            try:
                product = await self._parse_product(url)
                self.products.append(product)
                self.product_index += 1
                return product
            except Exception as e:
                self.logger.debug(e)
                self.logger.debug(f"restarting browser attempt: {attempt}")
                await self.stop_browser()

                # Не запускаем ещё один браузер после последней неудачной попытки.
                if attempt == 2:
                    raise

                await self.start_browser()

    async def start_browser(self) -> None:
        if self.context is not None:
            return

        self.logger.info("Starting browser...")



        camoufox = self._browser_manager(headed=self.headed)
        try:
            self.context = await camoufox.start()
            self._camoufox = camoufox
        except Exception:
            # Если запуск завершился ошибкой, не оставляем ссылку на менеджер.
            self.context = None
            self._camoufox = None
            raise

    async def stop_browser(self):
        self.logger.info("Stopping browser...")
        camoufox, self._camoufox = self._camoufox, None
        context, self.context = self.context, None

        try:
            if camoufox is not None:
                # Не ограничиваемся context.close(): завершаем и Playwright driver.
                await camoufox.__aexit__(None, None, None)
            elif context is not None:
                # Резервный путь для контекста, созданного вне этого менеджера.
                await context.close()
        except Exception as e:
            self.logger.error(f"error while closing Camoufox: {e}")
        finally:
            self.browser = None

    async def check_authentication(self):
        page = None

        try:
            page = await self.context.new_page()
            await page.goto("https://www.ozon.ru/my/main/", wait_until="domcontentloaded", timeout=30000)
            # Проверяем только нужный текст в DOM, не копируя всю HTML-страницу
            # в Python и не создавая дополнительную большую строку через .lower().
            login_prompt = await page.get_by_text(
                re.compile(r"войдите\s+или\s+зарегистрируйтесь", re.IGNORECASE)
            ).count()
            self.authentication = login_prompt == 0
            if self.authentication:
                self.logger.debug("Authentication successful")
            else:
                self.logger.debug("Authentication failed")
            return self.authentication
        except TimeoutError:
            self.logger.error("Timed out while waiting for page to load to check authentication")
            self.authentication = False
        except PlaywrightTimeoutError:
            self.logger.error("Timed out while waiting for page to load to check authentication")
            self.authentication = False
        except Exception as e:
            self.logger.error(f"error while trying to check authentication: {e}")
            self.authentication = False
        finally:
            if page:
                await page.close()

    async def _extract_title(self, page) -> str:
        try:
            await page.wait_for_selector("h1", timeout=30000)
            title_elem = await page.query_selector("h1")
            if title_elem:
                title = await title_elem.text_content()
                return title.strip() if title else "неизвестно"
        except Exception as e:
            self.logger.debug(e)

        return "неизвестно"

    async def _extract_price(self, page):
        price = "ошибка"

        try:
            # Не вызываем page.content(): он сериализует весь DOM в большую
            # Python-строку, которая здесь для извлечения цены не нужна.
            price_selectors = [
                '[data-widget="webPrice"]',
                '[data-widget="textBlock"]',
                '[data-widget="error"]',
                '[data-widget="webOutOfStock"]',
                #"[data-widget='price']",
                #".price",
                #"[class*='price']",
                #".c3118",
                #".yo3",
            ]

            available_texts = ["товар закончился",
                               "не доставляется в ваш регион",
                               "такой страницы не существует",
                               "этот товар закончился",
                               "товар не доставляется в ваш регион"]



            try:
                selector = await wait_for_any(page, price_selectors, timeout=40000)
                if selector == price_selectors[1] or selector == price_selectors[2] or selector == price_selectors[3]:
                    price = re.sub(r'\s', ' ', (await page.locator(selector).inner_text()).strip().lower())

                    if price not in available_texts:
                        price = "ошибка"

                        try:
                            selectors = price_selectors[:1] + price_selectors[2:]
                            selector = await wait_for_any(page, selectors, timeout=40000)
                        except Exception:
                            pass
                    elif price == available_texts[2]:
                        price = "страницы не существует"
                    elif price == available_texts[3]:
                        price = "товар закончился"
                    elif price == available_texts[4]:
                        price = "товар не доставляется в ваш регион"

                if selector == price_selectors[2]:
                    price = "страницы не существует"
                elif selector == price_selectors[3]:
                    price = "товар закончился"
                elif selector == price_selectors[0]:
                    try:
                        unavailable_selector = price_selectors[3]

                        if await page.locator(unavailable_selector).count() > 0:
                            price = "товар закончился"

                            if price not in available_texts:
                                unavailable_selector = None
                        else:
                            unavailable_selector = None
                    except Exception:
                        unavailable_selector = None
                    if unavailable_selector is None:
                        price_elem = await page.query_selector(selector)
                        if price_elem:
                            price_text = await price_elem.text_content()
                            if price_text:
                                price_match = re.search(
                                    r"(\d+(?:[^\S\r\n]+\d{3})*(?:[.,]\d{2})?)\s*(?:₽|руб\b|RUB\b)",
                                    price_text, re.IGNORECASE,
                                )
                                if price_match:
                                    price = "".join(price_match[1].split()).replace(",", ".")

            except Exception as e:
                self.logger.debug(e)

        except Exception as e:
            self.logger.error(f"❌ Ошибка извлечения цены: {e}")

        return price

    async def _parse_product(self, url: str):
        page = None
        product = {"title": "неизвестно",
                   "url": url,
                   "price": "ошибка"}

        for attempt in range(2):
            try:
                page = await self.context.new_page()

                try:
                    response = await page.goto(url, wait_until="domcontentloaded", timeout=40000)
                    if response and response.status in (404, 410):
                        product["price"] = "страницы не существует"
                        return product
                    if response and not response.ok:
                        raise ValueError(f"Ozon: HTTP {response.status}")
                except TimeoutError:
                    await page.close()
                    page = None
                    self.logger.error(f"страница не загрузилась за отведенное время попытка: {attempt}")
                    continue
                except PlaywrightTimeoutError:
                    await page.close()
                    page = None
                    self.logger.error(f"страница не загрузилась за отведенное время попытка: {attempt}")
                    continue
                except Exception as e:
                    await page.close()
                    page = None
                    self.logger.error(f"error while trying to open page: {e}")
                    raise e

                #title = await self._extract_title(page)

                price = await self._extract_price(page)

                #product["title"] = title
                product["price"] = price

                if product["price"] == "ошибка":
                    self.logger.warning("price was not parse, retrying...")
                    await page.close()
                    page = None
                    continue

                #self.logger.info(f"successful: {title[:50]}... | price: {product["price"]} ₽")
                self.logger.info(f"successful price: {product["price"]} ₽")

                await page.close()
                page = None
                break
            except TimeoutError:
                self.logger.error(f"timeout while parsing {url}")
            except PlaywrightTimeoutError:
                self.logger.error(f"timeout while parsing {url}")
            except Exception as e:
                self.logger.error(f"❌ parsing error: {e}")
            finally:
                if not (page is None):
                    await page.close()

        if product["price"] == "ошибка":
            self.logger.warning("price was not parse")
            raise Exception("connection error")

        return product
