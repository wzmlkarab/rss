import asyncio
import re
import aiohttp
import xml.etree.ElementTree as ET
from urllib.parse import parse_qs, quote, urlencode, urlparse
from lxml import etree

visited_links = []


async def fetch_html(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            html_content = await response.text()
            return html_content


async def extract_links(html_content):
    parser = etree.HTMLParser()
    tree = etree.fromstring(html_content, parser)
    text_content = tree.xpath("//text()")
    regex_pattern = r'\bhttps:\/\/\S*gdtot\S*\d+\b'

    links = set()
    for text in text_content:
        link_matches = re.findall(regex_pattern, text)
        links.update(link_matches)

    return links


async def process_link(link):
    base_link = "https://wzmlgdtot.onrender.com/link?url={}"
    encoded_url = quote(link, safe="")
    link = base_link.format(encoded_url)
    async with aiohttp.ClientSession() as session:
        async with session.get(link) as response:
            html_content = await response.content.read()
            parser = etree.HTMLParser()
            tree = etree.fromstring(html_content, parser)
            xpath_expression = '//*[@id="drive-link"]/@value'
            result = tree.xpath(xpath_expression)
            if result:
                gdrive_link = result[0]
                return gdrive_link


async def fetch_feed(feed_url):
    async with aiohttp.ClientSession() as session:
        async with session.get(feed_url) as response:
            feed_data = await response.text()

    new_entries = []
    filtered_words = ['Re:', 'ALBUM', 'Album', 'album', 'SONGS', 'Songs', 'songs', 'SONG', 'Song',
                      'song', 'MUSIC', 'Music', 'music', 'FLAC', 'flac', 'WAV', 'wav', 'Remix', 'remix', 'REMIX']
    # Parse XML data using ElementTree
    root = ET.fromstring(feed_data)

    for item in root.iter('item'):
        title = item.find('title').text
        link = item.find('link').text

        if link not in visited_links:
            visited_links.append(link)
            new_entries.append((title, link))
            if not any(word.lower() in title.lower() for word in filtered_words):
                parsed_url = urlparse(link)
                query_params = parse_qs(parsed_url.query)
                query_params['action'] = 'printpage'
                new_query_string = urlencode(query_params, doseq=True)
                new_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}?{new_query_string}#{parsed_url.fragment}"
                new_entries.append((title, new_url))

    return new_entries


async def main():
    feed_urls = [
        'https://ww1.sharespark.cfd/index.php?action=.xml;type=rss'
    ]

    while True:
        tasks = [fetch_feed(feed_url) for feed_url in feed_urls]
        results = await asyncio.gather(*tasks)

        for entries in results:
            for title, link in entries:
                # Fetch the HTML content asynchronously
                html_content = await fetch_html(link)

                # Extract the links asynchronously
                links = await extract_links(html_content)

                # Process each link asynchronously
                tasks = [process_link(link) for link in links]
                gdrive_links = await asyncio.gather(*tasks)

                # Print the processed links
                for link in gdrive_links:
                    if link:
                        print(link)

        # Delay between iterations (adjust as needed)
        await asyncio.sleep(60)  # Fetch updates every 60 seconds


# Run the main function
asyncio.run(main())
