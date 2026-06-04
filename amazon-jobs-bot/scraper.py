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
            url = f"https://www.jobsatamazon.co.uk/#/search?location={location}"
            await page.goto(url, timeout=60000)

            # wait for JS rendering
            await page.wait_for_timeout(8000)

            # scroll to trigger lazy loading
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_load_state("networkidle")
            await page.wait_for_timeout(10000)

            # 🔥 REAL DATA EXTRACTION (IMPORTANT FIX)
            cards_text = await page.evaluate("""
            () => {
                const bad = [
                    "amazon never requests",
                    "fraud",
                    "warning",
                    "skip",
                    "interested in applying",
                    "see all jobs",
                    "cookie",
                    "privacy",
                    "location"
                ];

                return Array.from(document.querySelectorAll('div'))
                    .map(el => el.innerText.trim())
                    .filter(t =>
                        t &&
                        t.length > 120 &&
                        t.length < 800 &&
                        !bad.some(b => t.toLowerCase().includes(b))
                    );
            }
            """)

            print("Potential job blocks:", len(cards_text))
            print("Sample:", cards_text[:3])

            # convert text blocks into pseudo jobs

            for text in cards_text[:50]:
                try:
                    lines = [l.strip() for l in text.split("\n") if len(l.strip()) > 3]

                    title = lines[0]

                    # reject obvious marketing text
                    reject_words = [
                        "apply", "interested", "see all", "amazon never", "warning"
                    ]

                    if any(w in title.lower() for w in reject_words):
                        continue

                    if len(title) < 10:
                        continue

                    job_id = hashlib.md5(title.encode()).hexdigest()

                    jobs.append({
                        "id": job_id,
                        "title": title,
                        "location": location,
                        "pay": "See listing",
                        "url": url
                    })

                except:
                    continue
           
        except Exception as e:
            print(f"Scraping error: {e}")

        finally:
            await browser.close()

    return jobs