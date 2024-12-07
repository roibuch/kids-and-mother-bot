import pandas as pd
import random
import datetime
import asyncio
from pytz import timezone
from telegram import Bot
from telegram.constants import ParseMode
import requests
import logging

# אתחול לוגים
logging.basicConfig(filename='bot_errors.log', level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

# טוקן של הבוט בטלגרם
TELEGRAM_BOT_TOKEN = "7949448573:AAE7CrDbjmhf8vlv8rCwygqFtBsXVIT4kLE"
TELEGRAM_CHAT_ID = "@babymotherdeals"  # המשתמש של הערוץ החדש

# אתחול הבוט
bot = Bot(token=TELEGRAM_BOT_TOKEN)

# אזור הזמן של ירושלים
jerusalem_tz = timezone("Asia/Jerusalem")

# טווח ימים לטעינת זמנים מראש
FETCH_DAYS = 30
shabbat_holiday_times = []

# פונקציה למשיכת זמני שבת וחגים מה-API
def fetch_shabbat_holiday_times():
    try:
        print("🔄 Fetching shabbat and holiday times...")
        url = f"https://www.hebcal.com/shabbat?cfg=json&geonameid=281184&start={datetime.datetime.now().strftime('%Y-%m-%d')}&end={(datetime.datetime.now() + datetime.timedelta(days=FETCH_DAYS)).strftime('%Y-%m-%d')}&M=on"
        response = requests.get(url, timeout=10)
        data = response.json()
        times = []
        for item in data.get("items", []):
            if item["category"] in ["candles", "havdalah"]:
                start_time = datetime.datetime.fromisoformat(item["date"]).astimezone(jerusalem_tz)
                end_time = start_time + datetime.timedelta(hours=25) if item["category"] == "candles" else start_time
                times.append({
                    "name": item["title"],
                    "start": start_time,
                    "end": end_time
                })
        print(f"✅ Loaded {len(times)} shabbat/holiday times.")
        return times
    except Exception as e:
        print(f"❌ Error fetching shabbat/holiday times: {e}")
        logging.error(f"Error fetching shabbat/holiday times: {e}")
        return []

# פונקציה לבדיקה אם שבת
def is_shabbat():
    now = datetime.datetime.now(jerusalem_tz)
    for time in shabbat_holiday_times:
        if time["start"] <= now <= time["end"]:
            return True
    return False

# פונקציה לבדוק אם URL תקין
def is_url_accessible(url):
    try:
        response = requests.get(url, allow_redirects=True, timeout=5)
        return response.status_code == 200
    except Exception as e:
        logging.error(f"Error checking URL {url}: {e}")
        return False

# פונקציה לשליחת הודעה בטלגרם
async def send_ad():
    remaining_ads = [ad for ad in ads if ad not in sent_ads]
    if not remaining_ads:
        print("✅ כל ההודעות נשלחו.")
        return

    chosen_ad = random.choice(remaining_ads)
    sent_ads.append(chosen_ad)

    ad_text = chosen_ad.get("Ad Text", "No Text")
    image_url = chosen_ad.get("Image URL")

    if is_shabbat():
        print("📛 שבת - לא ניתן לשלוח הודעות.")
        return

    try:
        if pd.notna(image_url) and is_url_accessible(image_url):
            await bot.send_photo(chat_id=TELEGRAM_CHAT_ID, photo=image_url, caption=ad_text, parse_mode=ParseMode.HTML)
        else:
            await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=ad_text, parse_mode=ParseMode.HTML)
        print(f"✅ הודעה נשלחה בהצלחה: {ad_text[:30]}...")
    except Exception as e:
        logging.error(f"Error sending ad: {e}")

# קריאת הנתונים מקובץ Excel
file_path = 'generated_ads.xlsx'
try:
    data = pd.read_excel(file_path)
    print(f"✅ הקובץ {file_path} נטען בהצלחה.")
except FileNotFoundError:
    print(f"❌ שגיאה: הקובץ {file_path} לא נמצא.")
    logging.error(f"FileNotFoundError: {file_path} not found.")
    exit()

# המרת ההודעות לרשימה
ads = data.to_dict(orient="records")
sent_ads = []

# לולאה לשליחת הודעות
async def send_ads_loop():
    global shabbat_holiday_times
    shabbat_holiday_times = fetch_shabbat_holiday_times()

    print("⏳ הבוט ממתין לשעה הראשונה לשליחה...")
    while True:
        now = datetime.datetime.now(jerusalem_tz)

        # בדיקה אם שבת
        if is_shabbat():
            print("📛 שבת - אין שליחת הודעות.")
        else:
            # שליחה בין 08:00 ל-23:00 כל 3 שעות
            if 8 <= now.hour <= 23 and now.hour % 2 == 0 and now.minute == 0:
                await send_ad()

        # המתנה של דקה לבדיקה חוזרת
        await asyncio.sleep(60)

# הרצת הבוט
async def run_bot():
    print("🚀 הבוט פעיל ומתחיל לשלוח הודעות...")
    try:
        await send_ads_loop()
    except Exception as e:
        logging.error(f"Critical error in bot loop: {e}")

if __name__ == "__main__":
    asyncio.run(run_bot())
