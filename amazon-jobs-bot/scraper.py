import asyncio
import hashlib
import json
from playwright.async_api import async_playwright

BASE_URL = "https://www.jobsatamazon.co.uk"


# -----------------------------
# 🔥 RECURSIVE EXTRACTOR (FALLBACK ONLY)
# -----------------------------
def extract_jobs(obj, location):
    jobs = []

    if isinstance(obj, dict):

        # only fallback detection
        if obj.get("title") or obj.get("jobTitle") or obj.get("name"):
            job = normalize_job(obj, location)
            if job:
                jobs.append(job)

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

            await page.goto(url, timeout=60000, wait_until="domcontentloaded")

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

            await page.wait_for_timeout(20000)
            await page.wait_for_load_state("networkidle")

            print("Current URL:", page.url)
            print("Page Title:", await page.title())
            print("Collected GraphQL responses:", len(graphql_data))

            # -----------------------------
            # 🔥 DEBUG SAMPLE (optional)
            # -----------------------------
            print("\n=== GRAPHQL STRUCTURE SAMPLE ===")
            for entry in graphql_data[:1]:
                if isinstance(entry, dict) and "data" in entry:
                    print(json.dumps(entry["data"], indent=2)[:2000])

            await browser.close()

            # -----------------------------
            # 🔥 FINAL EXTRACTION (IMPORTANT FIX)
            # -----------------------------
            print("\n=== EXTRACTING JOBS FROM GRAPHQL ===")

            jobs = []

            for entry in graphql_data:
                if not isinstance(entry, dict):
                    continue

                data = entry.get("data", {})

                # 🔥 THIS IS THE REAL SOURCE
                if isinstance(data, dict):
                    if "searchJobCardsByLocation" in data:
                        cards = data["searchJobCardsByLocation"].get("jobCards", [])
                        jobs.extend(cards)
                    else:
                        jobs.extend(extract_jobs(data, location))

            jobs = [j for j in jobs if j]

            unique = {}
            for j in jobs:
                if isinstance(j, dict) and j.get("jobId"):
                    unique[j["jobId"]] = j

            jobs = list(unique.values())

            print(f"Total jobs scraped: {len(jobs)}")

            return jobs

        except Exception as e:
            print("Scraping error:", e)
            await browser.close()
            return []


# -----------------------------
# 🔥 NORMALIZER (FINAL FIXED)
# -----------------------------
def normalize_job(job, location):
    try:
        title = job.get("jobTitle") or job.get("title") or "Amazon Job"

        job_id = hashlib.md5(
            str(job.get("jobId") or title + location).encode()
        ).hexdigest()

        # real GraphQL does NOT give URL → construct it
        url = (
            f"https://www.jobsatamazon.co.uk/job/{job.get('jobId')}"
            if job.get("jobId")
            else "N/A"
        )

        pay = job.get("totalPayRateMinL10N") or job.get("totalPayRateMin") or "See listing"

        city = job.get("city") or location

        return {
            "id": job_id,
            "title": title,
            "location": city,
            "url": url,
            "pay": pay
        }

    except Exception:
        return None


if __name__ == "__main__":
    result = asyncio.run(get_amazon_jobs("London"))

    print("\nRESULTS")
    print("=" * 50)

    for job in result[:10]:
        print(job)