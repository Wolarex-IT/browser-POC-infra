from contextlib import asynccontextmanager
from os import environ

from fastapi import Body, FastAPI, Request, HTTPException, Depends
from pydantic import HttpUrl
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError, Browser

BROWSER_URL = environ.get("BROWSER_URL", "http://127.0.0.1:9222")


@asynccontextmanager
async def lifespan(fastapi_app: FastAPI):
    playwright_driver = await async_playwright().start()
    fastapi_app.state.playwright_driver = playwright_driver

    browser = await playwright_driver.chromium.connect_over_cdp(BROWSER_URL)
    fastapi_app.state.browser = browser

    yield

    await browser.close()
    await playwright_driver.stop()


app = FastAPI(lifespan=lifespan)


def get_browser(request: Request) -> Browser:
    return request.app.state.browser


@app.post("/")
async def parse_url(
    url: HttpUrl = Body(),
    browser: Browser = Depends(get_browser)
) -> str:
    context = await browser.new_context()
    page = await context.new_page()

    try:
        await page.goto(str(url), timeout=15000)
        html = await page.content()
        return html
    except PlaywrightTimeoutError:
        raise HTTPException(status_code=504, detail="Website timeout")
    finally:
        await context.close()
