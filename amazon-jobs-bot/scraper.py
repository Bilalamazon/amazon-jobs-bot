import asyncio
import hashlib
from playwright.async_api import async_playwright

BASE_URL = "https://www.jobsatamazon.co.uk"


async def get_amazon_jobs(location="London"):
    jobs = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
            ]
        )

        page = await browser.new_page()

        await page.set_extra_http_headers({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        })

        url = f"{BASE_URL}/en/locations/{location.lower()}"

        try:
            print(f"Opening: {url}")

            await page.goto(
                url,
                timeout=60000,
                wait_until="domcontentloaded"
            )

            await page.wait_for_timeout(10000)

            print("Current URL:", page.url)

            # Screenshot for debugging
            await page.screenshot(
                path="debug.png",
                full_page=True
            )

            # Save rendered HTML
            html = await page.content()

            with open("debug.html", "w", encoding="utf-8") as f:
                f.write(html)

            print("HTML length:", len(html))

            # Print frames
            print("\n=== FRAMES ===")
            for frame in page.frames:
                print(frame.url)

            # Print links
            links = await page.query_selector_all("a")

            print("\n=== LINK DEBUG ===")
            print("Total links:", len(links))

            for link in links[:50]:
                try:
                    href = await link.get_attribute("href")
                    text = (await link.inner_text()).strip()
                    print("TEXT:", text[:50], "| HREF:", href)
                except Exception:
                    pass

            print("\n=== JOB EXTRACTION ===")

            seen = set()

            for link in links:
                try:
                    href = await link.get_attribute("href")

                    if not href:
                        continue

                    if "/job/" not in href and "/jobs/" not in href:
                        continue

                    title = (await link.inner_text()).strip()

                    if len(title) < 3:
                        title = "Amazon Job"

                    if href.startswith("http"):
                        full_url = href
                    else:
                        full_url = BASE_URL + href

                    job_id = hashlib.md5(
                        full_url.encode()
                    ).hexdigest()

                    if job_id in seen:
                        continue

                    seen.add(job_id)

                    jobs.append({
                        "id": job_id,
                        "title": title,
                        "location": location,
                        "pay": "See listing",
                        "url": full_url
                    })

                except Exception as e:
                    print("Link parse error:", e)

            print(f"\nTotal jobs scraped: {len(jobs)}")

        except Exception as e:
            print("Scraping error:", e)

        finally:
            await browser.close()

    return jobs


if __name__ == "__main__":
    result = asyncio.run(get_amazon_jobs("London"))

    print("\nRESULTS")
    print("=" * 50)

    for job in result[:10]:
        print(job)