import asyncio
import hashlib
from playwright.async_api import async_playwright

BASE_URL = "https://www.jobsatamazon.co.uk"


async def get_amazon_jobs(location="London"):
    jobs = []
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

        async def handle_response(response):
            try:
                if "graphql" in response.url.lower():
                    try:
                        data = await response.json()
                        graphql_data.append(data)

                        print("\n=== GRAPHQL RESPONSE CAPTURED ===")
                        print("Keys:", list(data.keys()))

                    except Exception:
                        pass
            except Exception:
                pass

        page.on(
            "response",
            lambda response: asyncio.create_task(handle_response(response))
        )

        url = "https://www.jobsatamazon.co.uk/app#/jobSearch"

        try:
            print(f"Opening: {url}")

            await page.goto(
                url,
                timeout=60000,
                wait_until="domcontentloaded"
            )

            await page.wait_for_timeout(15000)

            print("Current URL:", page.url)
            print("Page Title:", await page.title())
            print("Collected GraphQL responses:", len(graphql_data))

            await browser.close()

            # -----------------------------
            # GRAPHQL JOB EXTRACTION
            # -----------------------------
            print("\n=== EXTRACTING JOBS FROM GRAPHQL ===")

            jobs = []

            for entry in graphql_data:
                if not isinstance(entry, dict):
                    continue

                if "data" not in entry:
                    continue

                data = entry["data"]

                if isinstance(data, dict):
                    for key, value in data.items():

                        if isinstance(value, list):
                            for job in value:
                                normalized = normalize_job(job, location)
                                if normalized:
                                    jobs.append(normalized)

                        elif isinstance(value, dict):
                            for k2, v2 in value.items():
                                if isinstance(v2, list):
                                    for job in v2:
                                        normalized = normalize_job(job, location)
                                        if normalized:
                                            jobs.append(normalized)

            # remove duplicates
            unique = {}
            for j in jobs:
                if j and j.get("url"):
                    unique[j["url"]] = j

            jobs = list(unique.values())

            print(f"Total jobs scraped: {len(jobs)}")

            return jobs

        except Exception as e:
            print("Scraping error:", e)
            await browser.close()
            return []


# -----------------------------
# 🔥 IMPROVED NORMALIZER (FIXED)
# -----------------------------
def normalize_job(job, location):
    try:
        title = (
            job.get("title")
            or job.get("name")
            or job.get("jobTitle")
            or "Amazon Job"
        )

        job_id_raw = job.get("id") or job.get("jobId") or title + location
        job_id = hashlib.md5(str(job_id_raw).encode()).hexdigest()

        # 🔥 FIX: robust URL extraction
        url = (
            job.get("url")
            or job.get("jobUrl")
            or job.get("applyUrl")
            or job.get("externalUrl")
        )

        # fallback: nested links
        if not url and isinstance(job.get("links"), dict):
            url = (
                job["links"].get("apply")
                or job["links"].get("self")
            )

        return {
            "id": job_id,
            "title": title,
            "location": location,
            "url": url if url else "N/A",
            "pay": job.get("pay") or job.get("salary") or "See listing"
        }

    except Exception:
        return None


if __name__ == "__main__":
    result = asyncio.run(get_amazon_jobs("London"))

    print("\nRESULTS")
    print("=" * 50)

    for job in result[:10]:
        print(job)