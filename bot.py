import time
import requests
import os
import json
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Charger config persistante
if os.path.exists("config.json"):
    with open("config.json", "r") as f:
        config = json.load(f)
else:
    config = {"search_text": "jeans", "price_to": 20, "bot_active": True}

PARAMS = {
    "search_text": config["search_text"],
    "price_to": config["price_to"],
    "order": "newest_first",
    "per_page": 20
}

BOT_ACTIVE = config.get("bot_active", True)

# Charger seen pour éviter doublons
if os.path.exists("seen.json"):
    with open("seen.json", "r") as f:
        seen = set(json.load(f))
else:
    seen = set()

API_URL = "https://www.vinted.fr/api/v2/catalog/items"

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept": "application/json",
    "Referer": "https://www.vinted.fr/",
})

def save_config():
    config["search_text"] = PARAMS["search_text"]
    config["price_to"] = PARAMS["price_to"]
    config["bot_active"] = BOT_ACTIVE
    with open("config.json", "w") as f:
        json.dump(config, f)

def save_seen():
    with open("seen.json", "w") as f:
        json.dump(list(seen), f)

def send_telegram(title, price, url, image):
    caption = f"👕 {title}\n💰 Prix : {price}€\n🔗 {url}"
    requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendPhoto",
        data={
            "chat_id": CHAT_ID,
            "photo": image,
            "caption": caption
        }
    )
    print("Envoyé :", title, price)

def check_updates():
    global BOT_ACTIVE
    try:
        r = requests.get(f"https://api.telegram.org/bot{TOKEN}/getUpdates")
        data = r.json()
        if "result" in data and data["result"]:
            last_message = data["result"][-1]["message"]
            chat_id = last_message["chat"]["id"]
            text = last_message.get("text", "").lower()

            if text.startswith("prix "):
                try:
                    new_price = float(text.split()[1])
                    PARAMS["price_to"] = new_price
                    send_message(chat_id, f"Prix mis à jour : {new_price}€")
                    print(f"Prix mis à jour : {new_price}€")
                except:
                    pass

            elif text.startswith("ctg "):
                new_category = text.split(maxsplit=1)[1]
                PARAMS["search_text"] = new_category
                send_message(chat_id, f"Catégorie mise à jour : {new_category}")
                print(f"Catégorie mise à jour : {new_category}")

            elif text == "startbot":
                BOT_ACTIVE = True
                send_message(chat_id, "Bot démarré ✅")
                print("Bot démarré ✅")

            elif text == "stopbot":
                BOT_ACTIVE = False
                send_message(chat_id, "Bot arrêté ⏹️")
                print("Bot arrêté ⏹️")

            # Marquer updates comme lus
            last_update_id = data["result"][-1]["update_id"]
            requests.get(f"https://api.telegram.org/bot{TOKEN}/getUpdates?offset={last_update_id + 1}")

        save_config()
    except Exception as e:
        print("Erreur check_updates:", e)

def send_message(chat_id, text):
    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", data={"chat_id": chat_id, "text": text})

def scan_vinted():
    session.get("https://www.vinted.fr/")
    r = session.get(API_URL, params=PARAMS)
    if r.status_code != 200:
        print("Erreur API:", r.status_code, r.text[:200])
        return
    data = r.json()
    items = data["items"]
    for item in items:
        item_id = item["id"]
        if item_id in seen:
            continue
        seen.add(item_id)
        title = item["title"]
        price = int(float(item["price"]["amount"]))
        image = item["photo"]["url"]
        url = f"https://www.vinted.fr/items/{item_id}"
        send_telegram(title, price, url, image)
    save_seen()

# --- Boucle principale pour plusieurs scans ---
NUM_SCANS = 5
SLEEP_BETWEEN = 20  # secondes
for _ in range(NUM_SCANS):
    check_updates()
    if BOT_ACTIVE:
        scan_vinted()
    else:
        print("Bot en pause ⏸️")
    time.sleep(SLEEP_BETWEEN)
