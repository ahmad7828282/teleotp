import requests
import json
import time
import re
import threading

# ==============================
# CONFIG
# ==============================

STREAM_URL = "http://31.14.140.157:20785/panel/numbers/seedSMS?apikey=freetrail"
BOT_TOKEN = "8686041635:AAGZbSDzooDWmpS38t0jAi-HJAfVnSp7ZI4"
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# ==============================
# STORAGE
# ==============================

available_numbers = set()
active_numbers = {}  # number -> user_id
last_update_id = None

# ==============================
# TELEGRAM
# ==============================

def send_message(chat_id, text):
    requests.post(f"{BASE_URL}/sendMessage", data={
        "chat_id": chat_id,
        "text": text
    })

# ==============================
# HELPERS
# ==============================

def extract_otp(message):
    match = re.search(r'\d{4,8}', message)
    return match.group(0) if match else "N/A"

# ==============================
# STREAM LISTENER
# ==============================

def listen_stream():
    while True:
        try:
            with requests.get(STREAM_URL, stream=True, timeout=60) as response:
                for line in response.iter_lines():
                    if line:
                        decoded = line.decode("utf-8")

                        if decoded.startswith("data:"):
                            raw_json = decoded.replace("data: ", "")
                            try:
                                data = json.loads(raw_json)
                                number = data.get("number")
                                message = data.get("sms", "")

                                if number:

                                    # أضف الرقم لقائمة المتاح
                                    if number not in active_numbers:
                                        available_numbers.add(number)

                                    # إذا الرقم مخصص لمستخدم
                                    if number in active_numbers:
                                        user_id = active_numbers[number]
                                        otp = extract_otp(message)

                                        send_message(
                                            user_id,
                                            f"📩 Code received for {number}\n\nOTP: {otp}\n\nFull message:\n{message}"
                                        )

                                        # بعد إرسال الكود نحذف الحجز
                                        del active_numbers[number]

                            except:
                                pass
        except:
            time.sleep(5)

# ==============================
# BOT COMMAND HANDLER
# ==============================

def handle_updates():
    global last_update_id

    while True:
        try:
            params = {"timeout": 30}
            if last_update_id:
                params["offset"] = last_update_id + 1

            r = requests.get(f"{BASE_URL}/getUpdates", params=params)
            data = r.json()

            for update in data.get("result", []):
                last_update_id = update["update_id"]

                if "message" in update:
                    chat_id = update["message"]["chat"]["id"]
                    text = update["message"].get("text", "")

                    if text == "/start":
                        send_message(chat_id, "Send /get to receive a number.")

                    elif text == "/get":
                        if available_numbers:
                            number = available_numbers.pop()
                            active_numbers[number] = chat_id
                            send_message(chat_id, f"📞 Your number:\n{number}\n\nWaiting for code...")
                        else:
                            send_message(chat_id, "❌ No numbers available right now.")

        except:
            time.sleep(3)

# ==============================
# RUN
# ==============================

if __name__ == "__main__":
    t1 = threading.Thread(target=listen_stream)
    t2 = threading.Thread(target=handle_updates)

    t1.start()
    t2.start()

    t1.join()
    t2.join()