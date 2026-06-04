from playwright.async_api import async_playwright
import hashlib


async def get_amazon_jobs(location="London"):
    jobs = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        await page.set_extra_http_headers({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0'
        })

        try:
            await page.goto(
                f'https://www.jobsatamazon.co.uk/#/search?location={location}',
                timeout=30000
            )

            await page.wait_for_timeout(3000)

            job_cards = await page.query_selector_all('[class*="job-tile"]')

            for card in job_cards:
                title_el = await card.query_selector('[class*="job-title"]')
                location_el = await card.query_selector('[class*="location"]')
                pay_el = await card.query_selector('[class*="pay"]')
                link_el = await card.query_selector('a')

                title = await title_el.inner_text() if title_el else 'N/A'
                loc = await location_el.inner_text() if location_el else location
                pay = await pay_el.inner_text() if pay_el else 'See listing'

                url = await link_el.get_attribute('href') if link_el else ''

                job_id = hashlib.md5(f"{title}{loc}".encode()).hexdigest()

                jobs.append({
                    'id': job_id,
                    'title': title,
                    'location': loc,
                    'pay': pay,
                    'url': f"https://www.jobsatamazon.co.uk{url}"
                })

        except Exception as e:
            print(f"Scraping error: {e}")

        finally:
            await browser.close()

    return jobs