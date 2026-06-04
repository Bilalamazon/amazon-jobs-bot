from playwright.sync_api import sync_playwright
import hashlib

BASE_URL = "https://www.jobsatamazon.co.uk"


def get_amazon_jobs(location="london"):
    jobs = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        url = f"{BASE_URL}/en/locations/{location}"
        page.goto(url, wait_until="networkidle")

        page.wait_for_timeout(4000)

        links = page.query_selector_all("a")

        seen = set()

        for link in links:
            href = link.get_attribute("href")
            title = link.inner_text().strip()

            if not href or "/job" not in href:
                continue

            full_url = href if href.startswith("http") else BASE_URL + href

            job_id = hashlib.md5(full_url.encode()).hexdigest()
            if job_id in seen:
                continue
            seen.add(job_id)

            jobs.append({
                "id": job_id,
                "title": title,
                "location": location,
                "url": full_url
            })

        browser.close()

    return jobs