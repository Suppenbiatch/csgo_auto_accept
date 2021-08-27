import asyncio

from pyppeteer import launch
from pyppeteer.browser import Browser
from pyppeteer.errors import TimeoutError as PyTimeoutError
from pyppeteer.page import Page, ElementHandle
from pyppeteer_stealth import stealth


async def wait_for_ready(page: Page):
    while True:
        info = await page.evaluate("document.readyState")
        if info == 'complete':
            break
        await asyncio.sleep(0.5)
    try:
        await page.waitForSelector('div[id*=usercentrics-root]', visible=True, timeout=1000)
    except PyTimeoutError:
        return
    button = await page.evaluateHandle("""() => document.querySelector('#usercentrics-root').shadowRoot.querySelector('button[data-testid="uc-accept-all-button"]')""")
    if isinstance(button, ElementHandle):
        await button.click()
    return


async def add_match(sharecode, use_signal: bool = True):
    browser = await launch(headless=False,
                           handleSIGINT=use_signal,
                           handleSIGTERM=use_signal,
                           handleSIGHUP=use_signal,
                           defaultViewport={'width': 600, 'height': 300})

    matches = await add_match_parser(browser, sharecode)
    await browser.close()
    return matches


async def add_match_parser(browser: Browser, sharecodes):
    url = f'https://csgostats.gg/'
    page = await browser.newPage()
    await stealth(page)
    await page.goto(url)
    await wait_for_ready(page)
    if isinstance(sharecodes, str):
        sharecodes = [sharecodes]
    for sharecode in sharecodes:
        await page.evaluate(f'add_match("{sharecode}")')
    while True:
        matches = await page.evaluate('matches')
        if len(matches) != 0:
            status_in_all_matches = []
            for match in matches:
                if 'msg' in match:
                    status_in_all_matches.append(True)
                else:
                    status_in_all_matches.append(False)
            if all(status_in_all_matches):
                break
        await asyncio.sleep(0.5)
    await page.close()
    return matches


if __name__ == '__main__':
    async def main():
        # 'CSGO-a74aG-3Mr7o-qrbBa-77DGK-VTTrC'  # uncompletable, valid sharecode
        r = await add_match(['CSGO-6LYAh-Wo7ED-X4mfd-Qxoo2-2zYUN', ], use_signal=False)
        print(r)


    asyncio.run(main())
