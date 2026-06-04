from playwright.sync_api import sync_playwright
import hashlib


BASE_URL = "https://www.jobsatamazon.co.uk"


def clean_text(text):
    return " ".join(text.split()) if text else None


def scrape_london_jobs():
    jobs = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        url = f"{BASE_URL}/en/locations/london"
        print("Opening:", url)

        page.goto(url, wait_until="networkidle")

        # Wait for any job links to appear
        page.wait_for_timeout(5000)

        # Grab all links (site is JS rendered, so this is safest)
        links = page.query_selector_all("a")

        seen = set()

        for link in links:
            href = link.get_attribute("href")
            title = clean_text(link.inner_text())

            # Only keep job links
            if not href or "/job" not in href:
                continue

            full_url = href if href.startswith("http") else BASE_URL + href

            # prevent duplicates
            job_id = hashlib.md5(full_url.encode()).hexdigest()
            if job_id in seen:
                continue
            seen.add(job_id)

            # basic filtering to avoid junk links
            if len(title or "") < 5:
                continue

            jobs.append({
                "id": job_id,
                "title": title,
                "location": "London",
                "url": full_url
            })

        browser.close()

    return jobs


if __name__ == "__main__":
    jobs = scrape_london_jobs()

    print(f"\nTotal jobs found: {len(jobs)}\n")

    for job in jobs[:20]:
        print(job)