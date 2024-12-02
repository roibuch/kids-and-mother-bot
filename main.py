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

# קריאת זמני כניסת ויציאת שבת
try:
    shabbat_file_path = "shabbat_times.csv"
    shabbat_times = pd.read_csv(shabbat_file_path)
    shabbat_times["shabbat_start"] = pd.to_datetime(
        shabbat_times["shabbat_start"], format="%d/%m/%Y %H:%M", dayfirst=True
    ).dt.tz_localize("Asia/Jerusalem", ambiguous='NaT', nonexistent='NaT')
    shabbat_times["shabbat_end"] = pd.to_datetime(
        shabbat_times["shabbat_end"], format="%d/%m/%Y %H:%M", dayfirst=True
    ).dt.tz_localize("Asia/Jerusalem", ambiguous='NaT', nonexistent='NaT')
    print(f"✅ הקובץ {shabbat_file_path} נטען בהצלחה.")
except Exception as e:
    print(f"❌ שגיאה: לא ניתן לקרוא את הקובץ {shabbat_file_path}.")
    logging.error(f"Error reading {shabbat_file_path}: {e}")
    exit()

# אזור הזמן של ירושלים
jerusalem_tz = timezone("Asia/Jerusalem")

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

    try:
        if pd.notna(image_url) and is_url_accessible(image_url):
            await bot.send_photo(chat_id=TELEGRAM_CHAT_ID, photo=image_url, caption=ad_text, parse_mode=ParseMode.HTML)
        else:
            await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=ad_text, parse_mode=ParseMode.HTML)
        print(f"✅ הודעה נשלחה בהצלחה: {ad_text[:30]}...")
    except Exception as e:
        logging.error(f"Error sending ad: {e}")

# פונקציה לבדוק אם שבת
def is_shabbat():
    now = datetime.datetime.now(jerusalem_tz)
    for _, row in shabbat_times.iterrows():
        shabbat_start = row["shabbat_start"]
        shabbat_end = row["shabbat_end"]
        if shabbat_start <= now <= shabbat_end:
            return True
    return False

# לולאה לשליחת הודעות
async def send_ads_loop():
    print("⏳ הבוט מתחיל לשלוח הודעות...")
    while True:
        now = datetime.datetime.now(jerusalem_tz)

        # בדיקה אם שבת
        if is_shabbat():
            print("📛 שבת - אין שליחת הודעות.")
        else:
            # שליחה בין 08:00 ל-23:00 כל 3 שעות
            if 8 <= now.hour <= 23 and now.hour % 3 == 0 and now.minute == 0:
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
