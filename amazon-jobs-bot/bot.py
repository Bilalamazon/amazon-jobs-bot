import asyncio
import os
from dotenv import load_dotenv
from telegram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from scraper import get_amazon_jobs
from database import init_db, is_new_job, save_job


load_dotenv()

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# bot = Bot(token=TOKEN) 

from telegram.request import HTTPXRequest

request = HTTPXRequest(
    connect_timeout=30,
    read_timeout=30
)

bot = Bot(token=TOKEN, request=request)

SEARCH_LOCATION = "London"


async def check_jobs():
    print(f"Checking jobs in {SEARCH_LOCATION}...")

    jobs = await get_amazon_jobs(SEARCH_LOCATION)
    print(f"Total jobs scraped: {len(jobs)}")

    for job in jobs[:5]:
      print(job)
    new_count = 0

    for job in jobs:
        if is_new_job(job['id']):
            save_job(job['id'], job['title'], job['location'])
            await send_alert(job)
            new_count += 1
            await asyncio.sleep(1)

    print(f"Found {new_count} new jobs")


# async def send_alert(job):
#     message = (
#         f"New Amazon Job!\n"
#         f"Role: {job['title']}\n"
#         f"Location: {job['location']}\n"
#         f"Pay: {job['pay']}\n"
#         f"Apply: {job['url']}"
#     )

#     await bot.send_message(
#         chat_id=CHAT_ID,
#         text=message
#     )

async def send_alert(job):
    message = (
        f"New Amazon Job!\n"
        f"Role: {job['title']}\n"
        f"Location: {job['location']}\n"
        f"Pay: {job['pay']}\n"
        f"Apply: {job['url']}"
    )

    try:
        await bot.send_message(chat_id=CHAT_ID, text=message)
    except Exception as e:
        print(f"Telegram send failed: {e}")


async def main():
    init_db()

    await bot.send_message(
        chat_id=CHAT_ID,
        text=f"Bot started! Monitoring {SEARCH_LOCATION} every 30 mins."
    )

    await check_jobs()

    scheduler = AsyncIOScheduler()
    scheduler.add_job(check_jobs, 'interval', minutes=30)
    scheduler.start()

    while True:
        await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(main())