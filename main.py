from contextlib import asynccontextmanager

from cloakbrowser import launch_async
from fastapi import FastAPI, Request
from pydantic import HttpUrl


@asynccontextmanager
async def lifespan(app: FastAPI):
    browser = await launch_async()
    app.state.browser = browser
    yield
    await browser.close()


app = FastAPI(lifespan=lifespan)


@app.post("/")
async def parse_url(url: HttpUrl, request: Request):
    browser = request.app.state.browser

    page = await browser.new_page()
    await page.goto(str(url))
    html = await page.content()
    await page.close()

    return html
