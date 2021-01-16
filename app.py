import asyncio
import json
import os
import re
import sys
import time
from datetime import date

import matplotlib.pyplot as plt
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
        if await page.querySelector('#endOfListMarker') != None:
            return


async def get_item_info(item):
    def sanitize_field(original, case_check_only=False):
        if not case_check_only:
            original = re.sub(r'(, .*$)|( \(.*\))', '', original.strip().replace('\n', '').replace('de ', ''))

        return original.title() if original.isupper() or original.islower() else original
    
    
    async def more_info(url):
        browser = await launch()
        page = await browser.newPage()
        info = {}

        await page.setViewport({'width': 1920, 'height': 948})
        await page.goto(url)      
        await wait_loading('#detailBulletsWrapper_feature_div', page)
        
        details = await page.evaluate("() => document.querySelector('#detailBullets_feature_div ul').children.length")
        for i in range(details):
            feature = await page.querySelectorEval(f'#detailBullets_feature_div li:nth-of-type({i + 1})', "({ firstChild: { children } }) => { return ({ [children[0].textContent.replace(/\\n/g, '').slice(0, -1)]: children[1].textContent }); }")
            info.update(feature)

        try:
            info.update({(await page.querySelectorEval('#detailBulletsWrapper_feature_div ul:nth-of-type(2) li span.a-text-bold', "n => n.innerHTML.replace(/\\n/g, '').slice(0, -1)")): (await page.evaluate("() => `${document.querySelector('#acrPopover').title} - ${document.querySelector('#acrCustomerReviewText').textContent}`"))})
        except: pass

        await browser.close()
        return info


    _item = {
        'price': 0,
        'id': '',
        'url': '',
        'name': '',
        'pic': '',
        'author': '',
        'ok': True,
        'info': {}
    }

    _id = await page.evaluate("i => i.getAttribute('data-itemid')", item)
    url = f"document.querySelector('div#itemImage_{_id} a"

    _item['id'] = _id
    _item['price'] = await page.evaluate(f"i => Number(i.getAttribute('data-price'))", item)
    _item['url'] = await page.evaluate(f"i => {url}').href", item)
    _item['name'] = sanitize_field(await page.evaluate(f"i => {url}').title", item), True)
    _item['pic'] = await page.evaluate(f"i => {url} img').src", item)
    _item['author'] = sanitize_field(await page.evaluate(f"i => document.querySelector('span#item-byline-{_item['id']}').textContent", item))
    _item['info'] = await more_info(_item['url'])

    if abs(_item['price']) == float('inf'):
        _item['ok'] = False
        _item['price'] = 0

    return _item


def set_default(obj, key, val): obj[key] = val if not key in obj else obj[key]


def update_data(items, data):
    def get_new_prices(items):
        prices = []
        [ prices.append(item['price']) for item in items ]

        return [min(prices), max(prices)]
    def set_default_prices():
        dates = data['items']['dates']
        today = list(dates.keys())[-1]
        last = list(dates.keys())[-2]

        if len(dates[today]) == len(dates[last]): return
        elif len(dates[today]) > len(dates[last]):
            for item in list(filter(lambda item: item not in dates[last], dates[today])):
                if item in dates[last]:
                    dates[last][dates[last].index(item)]['ok'] = True
                else:
                    dates[last].append(item)
        else:
            for item in list(filter(lambda item: item not in dates[today], dates[last])):
                dates[last][dates[last].index(item)]['ok'] = False


    today = date.today().strftime('%Y/%m/%d')
    prices = get_new_prices(items)

    set_default(data, 'items', {})
    set_default(data['items'], 'dates', {})
    set_default(data['items'], 'prices', [])
    set_default(data['items']['dates'], today, [])

    data['items']['dates'][today] = items

    if len(data['items']['dates']) == 1 or data['items']['prices'] == [0, 0]:
        data['items']['prices'][0] = prices[0]
        data['items']['prices'][1] = prices[1]
    else:
        if prices[0] < data['items']['prices'][0]:
            data['items']['prices'][0] = prices[0]
        if prices[1] > data['items']['prices'][1]:
            data['items']['prices'][1] = prices[1]

    set_default_prices()

    json.dump(data, open('config.json', 'w'), ensure_ascii=False)
    os.remove('realtime.png')


def plot_graph(data):
    dates = data['dates']
    products = {}

    plt.xlabel('Dates')
    plt.ylabel('Prices')
    plt.title('Amazon wishlist items\' prices over time')


    for date in dates:
        for item in dates[date]:
            if not item['ok']: continue

            set_default(products, item['id'], [[], []])
            products[item['id']][0].append(date)
            products[item['id']][1].append(item['price'])

    for _id in products:
        plt.plot(products[_id][0], products[_id][1])

    plt.show()


async def main():
    global page
    data = json.load(open('config.json'))

    if not 'readonly' in sys.argv:
        browser = await launch()
        page = await browser.newPage()
        url = data['url']
        await page.setViewport({'width': 1920, 'height': 948})
        await page.goto(url)
        await wait_loading('#navFooter')
        await load_full_page()

        items = [await get_item_info(item) for item in await page.querySelectorAll('#g-items > li')]
        await browser.close()
        
        update_data(items, data)

    plot_graph(data['items'])


if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(main())
