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
# 🔥 SCRAPER (FINAL FIX)
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
        # 🔥 ROUTE INTERCEPTION (FIXED PROPERLY)
        # -------------------------------------------------
        async def handle_route(route, request):
            try:
                if "graphql" not in request.url.lower():
                    return await route.continue_()

                response = await route.fetch()

                try:
                    data = await response.json()
                except Exception:
                    return await route.continue_()

                # ONLY check structure, DO NOT filter jobCards here
                if (
                    isinstance(data, dict)
                    and "data" in data
                    and isinstance(data["data"], dict)
                    and "searchJobCardsByLocation" in data["data"]
                ):
                    graphql_data.append(data["data"])
                    print("Captured GraphQL payload")

                return await route.fulfill(response=response)

            except Exception:
                return await route.continue_()

        # IMPORTANT: attach BEFORE navigation
        await page.route("**/*", handle_route)

        url = f"{BASE_URL}/app#/jobSearch"

        try:
            print(f"Opening: {url}")

            await page.goto(url, timeout=60000, wait_until="domcontentloaded")

            await page.wait_for_timeout(4000)

            # -----------------------------
            # FORCE UI LOAD
            # -----------------------------
            try:
                await page.click("text=See all jobs", timeout=3000)
            except:
                try:
                    await page.click("text=Find your next job", timeout=3000)
                except:
                    pass

            # trigger lazy network calls
            await page.mouse.wheel(0, 4000)
            await page.wait_for_timeout(10000)
            await page.wait_for_load_state("networkidle")

            print(f"Collected GraphQL payloads: {len(graphql_data)}")

            await browser.close()

            # -----------------------------
            # EXTRACTION
            # -----------------------------
            print("\n=== EXTRACTING JOBS ===")

            all_jobs = []

            for block in graphql_data:
                job_cards = block.get("searchJobCardsByLocation", {}).get("jobCards", [])

                if job_cards:
                    all_jobs.extend(extract_jobs_from_cards(job_cards, location))

            # -----------------------------
            # DEDUP (SAFE)
            # -----------------------------
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