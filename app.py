import asyncio
import json
import time

from pyppeteer import launch

page = None


async def wait_loading(query, page=None):
    if page == None:
        page = globals()['page']

    element = await page.querySelector(query)

    while element == None:
        await page.screenshot({'path': 'realtime.png'})
        element = await page.querySelector(query)
        time.sleep(0.1)

    await page.screenshot({'path': 'realtime.png'})
    return element


async def load_full_page():
    while True:
        await page.querySelectorEval('#navFooter', 'f => f.scrollIntoView(false)')
        await page.screenshot({'path': 'realtime.png'})
        if await page.querySelector('#endOfListMarker') != None: return


async def get_item_info(item):
    res = {
        'price': 0,
        'id': '',
        'url': '',
        'name': '',
        'pic': '',
        'author': ''
    }

    res['id'] = await page.evaluate(f"i => i.getAttribute('data-itemid')", item)
    [res['price'], res['url'], res['name'], res['pic'], res['author']] = await page.evaluate(f"i => [Number(i.getAttribute('data-price')), document.querySelector('div#itemImage_{res['id']} a').href, document.querySelector('div#itemImage_{res['id']} a').title, document.querySelector('div#itemImage_{res['id']} a img').src, document.querySelector('span#item-byline-{res['id']}').innerHTML.replace('de ', '').includes(',') ? document.querySelector('span#item-byline-{res['id']}').innerHTML.replace('de ', '').split(',')[0] : document.querySelector('span#item-byline-{res['id']}').innerHTML.replace('de ', '').split(' (')[0]]", item)
    
    return res


async def main():
    global page

    browser = await launch()
    page = await browser.newPage()
    url = json.load(open('config.json'))['url']

    await page.setViewport({'width': 1920, 'height': 948})
    await page.goto(url)
    await wait_loading('#navFooter')
    await load_full_page()

    items = [await get_item_info(item) for item in await page.querySelectorAll('#g-items > li')]

    await browser.close()


if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(main())
