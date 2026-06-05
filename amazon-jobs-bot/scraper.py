import asyncio
import hashlib
from playwright.async_api import async_playwright

BASE_URL = "https://www.jobsatamazon.co.uk"


async def get_amazon_jobs(location="London"):
    jobs = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox"]
        )

        page = await browser.new_page()

        await page.set_extra_http_headers({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        })

        url = f"{BASE_URL}/en/locations/{location.lower()}"

        try:
            await page.goto(url, timeout=60000)

            # better than networkidle for JS sites
            await page.wait_for_timeout(6000)

            # grab ALL links first (site is SPA)
            links = await page.query_selector_all("a")

            seen = set()

            for link in links:
                try:
                    href = await link.get_attribute("href")
                    title = (await link.inner_text()).strip()

                    if not href or "/job" not in href:
                        continue

                    full_url = href if href.startswith("http") else BASE_URL + href

                    job_id = hashlib.md5(full_url.encode()).hexdigest()

                    if job_id in seen:
                        continue
                    seen.add(job_id)

                    # filter junk titles
                    if len(title) < 5:
                        continue

                    jobs.append({
                        "id": job_id,
                        "title": title,
                        "location": location,
                        "pay": "See listing",
                        "url": full_url
                    })

                except Exception:
                    continue

        except Exception as e:
            print("Scraping error:", e)

        await browser.close()

    return jobs


# quick local test
if __name__ == "__main__":
    result = asyncio.run(get_amazon_jobs("london"))
    print("Total jobs:", len(result))
    for j in result[:10]:
        print(j)