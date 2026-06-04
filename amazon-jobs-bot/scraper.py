import os
import asyncio
import hashlib
from playwright.async_api import async_playwright


async def ensure_browser():
    try:
        proc = await asyncio.create_subprocess_exec(
            "playwright", "install", "chromium"
        )
        await proc.communicate()
    except Exception as e:
        print("Browser install skipped or failed:", e)


async def get_amazon_jobs(location="London"):
    jobs = []

    await ensure_browser()

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox"]
        )

        page = await browser.new_page()

        await page.set_extra_http_headers({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
        })

        try:
            await page.goto(
                f"https://www.jobsatamazon.co.uk/#/search?location={location}",
                timeout=60000
            )

            await page.wait_for_load_state("networkidle")
            await page.wait_for_timeout(8000)

            # 🔥 DEBUG ONLY (keep for now)
            html = await page.content()
            print(html[:1000])

            # ❌ REMOVE THIS (it causes fake results)
            # job_cards = await page.query_selector_all("div")

            # ✅ TRY REAL SELECTOR (may need adjustment later)
            job_cards = await page.query_selector_all(
                "[class*='job'], [data-testid*='job'], [class*='Job']"
            )

            print("Total job-like elements:", len(job_cards))

            for card in job_cards:
                try:
                    title_el = await card.query_selector("h2, h3, [class*='title']")
                    location_el = await card.query_selector("[class*='location']")
                    pay_el = await card.query_selector("[class*='pay'], [class*='salary']")
                    link_el = await card.query_selector("a")

                    title = await title_el.inner_text() if title_el else None
                    loc = await location_el.inner_text() if location_el else location
                    pay = await pay_el.inner_text() if pay_el else "See listing"
                    url = await link_el.get_attribute("href") if link_el else ""

                    # 🔥 skip empty junk cards
                    if not title:
                        continue

                    job_id = hashlib.md5(f"{title}{loc}".encode()).hexdigest()

                    jobs.append({
                        "id": job_id,
                        "title": title,
                        "location": loc,
                        "pay": pay,
                        "url": f"https://www.jobsatamazon.co.uk{url}" if url else ""
                    })

                except:
                    continue

        except Exception as e:
            print(f"Scraping error: {e}")

        finally:
            await browser.close()

    return jobs