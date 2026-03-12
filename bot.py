import time
import requests
import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

seen = set()
BOT_ACTIVE = True  # par défaut le bot tourne

API_URL = "https://www.vinted.fr/api/v2/catalog/items"

PARAMS = {
    "search_text": "jeans",
    "price_to": 20,
    "order": "newest_first",
    "per_page": 20
}

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept": "application/json",
    "Referer": "https://www.vinted.fr/",
})


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
    """
    Vérifie les nouveaux messages Telegram et met à jour prix/catégorie/start/stop
    """
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
                    requests.post(
                        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                        data={"chat_id": chat_id, "text": f"Prix mis à jour : {new_price}€"}
                    )
                    print(f"Prix mis à jour : {new_price}€")
                except:
                    pass

            elif text.startswith("ctg "):
                new_category = text.split(maxsplit=1)[1]
                PARAMS["search_text"] = new_category
                requests.post(
                    f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                    data={"chat_id": chat_id, "text": f"Catégorie mise à jour : {new_category}"}
                )
                print(f"Catégorie mise à jour : {new_category}")

            elif text == "startbot":
                BOT_ACTIVE = True
                requests.post(
                    f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                    data={"chat_id": chat_id, "text": "Bot démarré ✅"}
                )
                print("Bot démarré ✅")

            elif text == "stopbot":
                BOT_ACTIVE = False
                requests.post(
                    f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                    data={"chat_id": chat_id, "text": "Bot arrêté ⏹️"}
                )
                print("Bot arrêté ⏹️")

            # 🔹 Marquer les updates comme lus pour éviter de bloquer le bot
            last_update_id = data["result"][-1]["update_id"]
            requests.get(f"https://api.telegram.org/bot{TOKEN}/getUpdates?offset={last_update_id + 1}")

    except Exception as e:
        print("Erreur check_updates:", e) 


def scan_vinted():
    session.get("https://www.vinted.fr/")

    r = session.get(API_URL, params=PARAMS)
    print("Status:", r.status_code)
    if r.status_code != 200:
        print("Réponse:", r.text[:200])
        return

    data = r.json()
    items = data["items"]

    for item in items:
        item_id = item["id"]
        if item_id in seen:
            continue
        seen.add(item_id)

        title = item["title"]
        price = int(float(item["price"]["amount"]))  # arrondi
        image = item["photo"]["url"]
        url = f"https://www.vinted.fr/items/{item_id}"

        send_telegram(title, price, url, image)


# Boucle principale
# Boucle principale adaptée pour GitHub Actions
while True:
    check_updates()  # récupère les nouveaux messages et met à jour prix/catégorie/start/stop
    if BOT_ACTIVE:
        try:
            scan_vinted()
        except Exception as e:
            print("Erreur scan_vinted :", e)
    else:
        print("Bot en pause... ⏸️")
    
    # Pause entre chaque cycle pour éviter d'être trop agressif
    time.sleep(20)
