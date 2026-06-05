import asyncio
import hashlib
import json
from playwright.async_api import async_playwright

BASE_URL = "https://www.jobsatamazon.co.uk"


# -----------------------------
# 🔥 NORMALIZER (ALWAYS SAFE OUTPUT)
# -----------------------------
def normalize_job(job, location):
    try:
        title = job.get("jobTitle") or job.get("title") or "Amazon Job"

        raw_job_id = job.get("jobId") or job.get("id") or (title + location)

        # stable internal id for bot tracking
        stable_id = hashlib.md5(str(raw_job_id).encode()).hexdigest()

        job_id = job.get("jobId")  # real Amazon id if exists

        return {
            "id": stable_id,          # bot-safe unique id
            "jobId": job_id,          # IMPORTANT for your bot logic
            "title": title,
            "location": job.get("city") or location,
            "url": (
                f"{BASE_URL}/job/{job_id}"
                if job_id
                else "N/A"
            ),
            "pay": (
                job.get("totalPayRateMinL10N")
                or job.get("totalPayRateMin")
                or "See listing"
            )
        }

    except Exception:
        return None


# -----------------------------
# 🔥 SCRAPER
# -----------------------------
async def get_amazon_jobs(location="London"):
    graphql_data = []

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

        # -----------------------------
        # 🔥 GRAPHQL CAPTURE
        # -----------------------------
        async def handle_response(response):
            try:
                if "graphql" in response.url.lower():
                    print("GRAPHQL HIT:", response.url)
                    try:
                        graphql_data.append(await response.json())
                    except Exception:
                        pass
            except Exception:
                pass

        page.on("response", lambda r: asyncio.create_task(handle_response(r)))

        url = f"{BASE_URL}/app#/jobSearch"

        try:
            print(f"Opening: {url}")

            await page.goto(url, timeout=60000, wait_until="domcontentloaded")
            await page.wait_for_timeout(5000)

            # -----------------------------
            # FORCE SPA LOAD
            # -----------------------------
            try:
                await page.click("text=See all jobs")
                print("Clicked: See all jobs")
            except:
                try:
                    await page.click("text=Find your next job")
                    print("Clicked: Find your next job")
                except:
                    print("No job button clicked (fallback mode)")

            await page.wait_for_timeout(20000)
            await page.wait_for_load_state("networkidle")

            print("Collected GraphQL responses:", len(graphql_data))

            await browser.close()

            # -----------------------------
            # 🔥 EXTRACTION (FIXED LOGIC)
            # -----------------------------
            print("\n=== EXTRACTING JOBS ===")

            jobs = []

            for entry in graphql_data:
                if not isinstance(entry, dict):
                    continue

                data = entry.get("data", {})

                # PRIMARY SOURCE (Amazon GraphQL)
                if isinstance(data, dict) and "searchJobCardsByLocation" in data:
                    cards = data["searchJobCardsByLocation"].get("jobCards", [])

                    for job in cards:
                        normalized = normalize_job(job, location)
                        if normalized:
                            jobs.append(normalized)

            # -----------------------------
            # CLEAN + DEDUP
            # -----------------------------
            cleaned = []
            seen = set()

            for j in jobs:
                if not j:
                    continue

                key = j.get("jobId") or j.get("id")

                if key and key not in seen:
                    seen.add(key)
                    cleaned.append(j)

            print(f"Total jobs scraped: {len(cleaned)}")

            return cleaned

        except Exception as e:
            print("Scraping error:", e)
            await browser.close()
            return []


# -----------------------------
# 🔥 RUN
# -----------------------------
if __name__ == "__main__":
    result = asyncio.run(get_amazon_jobs("London"))

    print("\nRESULTS")
    print("=" * 50)

    for job in result[:10]:
        print(job)