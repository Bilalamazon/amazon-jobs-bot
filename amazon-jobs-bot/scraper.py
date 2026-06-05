import asyncio
import hashlib
from playwright.async_api import async_playwright

BASE_URL = "https://www.jobsatamazon.co.uk"


# -----------------------------
# 🔥 NORMALIZER
# -----------------------------
def normalize_job(job, location):
    try:
        title = job.get("jobTitle") or job.get("title") or "Amazon Job"

        job_id = job.get("jobId")
        raw_id = job_id or (title + location)

        stable_id = hashlib.md5(str(raw_id).encode()).hexdigest()

        return {
            "id": stable_id,
            "jobId": job_id,
            "title": title,
            "location": job.get("city") or location,
            "url": f"{BASE_URL}/job/{job_id}" if job_id else "N/A",
            "pay": (
                job.get("totalPayRateMinL10N")
                or job.get("totalPayRateMin")
                or "See listing"
            )
        }
    except Exception:
        return None


# -----------------------------
# 🔥 EXTRACTOR
# -----------------------------
def extract_jobs_from_cards(job_cards, location):
    jobs = []

    for job in job_cards:
        if isinstance(job, dict):
            norm = normalize_job(job, location)
            if norm:
                jobs.append(norm)

    return jobs


# -----------------------------
# 🔥 SCRAPER (FIXED + STABLE)
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

        # -------------------------------------------------
        # 🔥 FIX 1: CAPTURE ONLY REAL JOB PAYLOADS
        # -------------------------------------------------
        async def handle_response(response):
            try:
                if "graphql" not in response.url.lower():
                    return

                data = await response.json()

                # safer checks (prevents empty payload issues)
                if (
                    isinstance(data, dict)
                    and "data" in data
                    and isinstance(data["data"], dict)
                ):
                    inner = data["data"]

                    block = inner.get("searchJobCardsByLocation")

                    if (
                        isinstance(block, dict)
                        and block.get("jobCards")
                    ):
                        graphql_data.append(inner)
                        print("Captured GraphQL payload")

            except Exception:
                pass

        page.on("response", lambda r: asyncio.create_task(handle_response(r)))

        url = f"{BASE_URL}/app#/jobSearch"

        try:
            print(f"Opening: {url}")

            await page.goto(url, timeout=60000, wait_until="domcontentloaded")

            # allow SPA init
            await page.wait_for_timeout(4000)

            # -------------------------------------------------
            # 🔥 FIX 2: FORCE UI TRIGGERS (IMPORTANT)
            # -------------------------------------------------
            try:
                await page.click("text=See all jobs", timeout=3000)
            except:
                try:
                    await page.click("text=Find your next job", timeout=3000)
                except:
                    pass

            # 🔥 FIX 3: force lazy GraphQL triggers
            await page.mouse.wheel(0, 5000)
            await page.wait_for_timeout(12000)

            # IMPORTANT: wait extra time for API bursts
            await page.wait_for_load_state("networkidle")
            await page.wait_for_timeout(5000)

            print(f"Collected GraphQL payloads: {len(graphql_data)}")

            await browser.close()

            # -------------------------------------------------
            # 🔥 EXTRACTION
            # -------------------------------------------------
            print("\n=== EXTRACTING JOBS ===")

            all_jobs = []

            for block in graphql_data:
                job_cards = (
                    block
                    .get("searchJobCardsByLocation", {})
                    .get("jobCards", [])
                )

                all_jobs.extend(extract_jobs_from_cards(job_cards, location))

            # -------------------------------------------------
            # 🔥 FIX 4: SAFE DEDUP (REAL jobId ONLY)
            # -------------------------------------------------
            seen = set()
            cleaned = []

            for j in all_jobs:
                job_id = j.get("jobId")

                if job_id and job_id not in seen:
                    seen.add(job_id)
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