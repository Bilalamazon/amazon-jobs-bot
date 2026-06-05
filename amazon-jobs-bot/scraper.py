import asyncio
import hashlib
from playwright.async_api import async_playwright

BASE_URL = "https://www.jobsatamazon.co.uk"


# -----------------------------
# 🔥 IMPROVED RECURSIVE EXTRACTOR
# -----------------------------
def extract_jobs(obj, location):
    jobs = []

    if isinstance(obj, dict):

        # 🔥 FIX: stricter job detection (prevents false positives)
        if (
            obj.get("title")
            or obj.get("jobTitle")
            or obj.get("name")
        ):
            job = normalize_job(obj, location)
            if job:
                jobs.append(job)

        # recurse deeper safely
        for v in obj.values():
            jobs.extend(extract_jobs(v, location))

    elif isinstance(obj, list):
        for item in obj:
            jobs.extend(extract_jobs(item, location))

    return jobs


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
                        data = await response.json()
                        graphql_data.append(data)

                    except Exception:
                        pass
            except Exception:
                pass

        page.on(
            "response",
            lambda response: asyncio.create_task(handle_response(response))
        )

        url = f"{BASE_URL}/app#/jobSearch"

        try:
            print(f"Opening: {url}")

            await page.goto(
                url,
                timeout=60000,
                wait_until="domcontentloaded"
            )

            # -----------------------------
            # 🔥 FORCE JOB LISTING LOAD
            # -----------------------------
            await page.wait_for_timeout(5000)

            try:
                await page.click("text=See all jobs")
                print("Clicked: See all jobs")
            except:
                try:
                    await page.click("text=Find your next job")
                    print("Clicked: Find your next job")
                except:
                    print("No job button clicked (fallback mode)")

            # allow GraphQL to fully load jobs
            await page.wait_for_timeout(25000)
            await page.wait_for_load_state("networkidle")

            print("Current URL:", page.url)
            print("Page Title:", await page.title())
            print("Collected GraphQL responses:", len(graphql_data))

            await browser.close()

            # -----------------------------
            # 🔥 GRAPHQL JOB EXTRACTION (FIXED)
            # -----------------------------
            print("\n=== EXTRACTING JOBS FROM GRAPHQL ===")

            jobs = []

            for entry in graphql_data:
                if isinstance(entry, dict) and "data" in entry:
                    data = entry["data"]

                    # 🔥 FIX: ensure full deep traversal
                    jobs.extend(extract_jobs(data, location))

                    if isinstance(data, dict):
                        for v in data.values():
                            jobs.extend(extract_jobs(v, location))

            jobs = [j for j in jobs if j]

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
# 🔥 NORMALIZER (UNCHANGED)
# -----------------------------
def normalize_job(job, location):
    try:
        title = (
            job.get("title")
            or job.get("jobTitle")
            or job.get("name")
            or "Amazon Job"
        )

        job_id_raw = job.get("id") or job.get("jobId") or title + location
        job_id = hashlib.md5(str(job_id_raw).encode()).hexdigest()

        url = (
            job.get("url")
            or job.get("jobUrl")
            or job.get("applyUrl")
            or job.get("externalUrl")
        )

        if not url and isinstance(job.get("links"), dict):
            url = (
                job["links"].get("apply")
                or job["links"].get("self")
                or job["links"].get("job")
            )

        if not url and isinstance(job.get("jobDetails"), dict):
            url = (
                job["jobDetails"].get("applyUrl")
                or job["jobDetails"].get("url")
                or job["jobDetails"].get("link")
            )

        if not url and job.get("id"):
            url = f"{BASE_URL}/job/{job.get('id')}"

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