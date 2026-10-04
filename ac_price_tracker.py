import time
import requests
from datetime import datetime

# ================= Configuration =================
ORIGIN = "SFO"
DESTINATION = "YVR"
DEPARTURE_DATE = "2027-03-26"  # YYYY-MM-DD
PRICE_THRESHOLD_CAD = 300.0
AIRLINE_CODE = "AC"            # Air Canada
POLL_INTERVAL_SECONDS = 3600   # Check once per hour

SERPAPI_KEY = "27a735b448c052c62a13fbb482291d59c76f27ff93e40b7e2564eaf25dbc3c73"

# --- Notification Channels (Set to True to enable) ---
ENABLE_DISCORD = True
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1556421980671185048/r_oqUX-3BbTdSFzcXDx1X4O3JD__xJ0pBl_bzRx2V2vxZ8vXDBY_tIOqYPDwNs0wL-gC"

ENABLE_TELEGRAM = False
TELEGRAM_BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
TELEGRAM_CHAT_ID = "YOUR_CHAT_ID_HERE"
# =================================================

def send_discord_notification(message):
    """Sends a formatted embed message to a Discord channel via Webhook."""
    payload = {
        "content": "🚨 **Air Canada Price Drop Detected!**",
        "embeds": [
            {
                "title": f"Flight Alert: {ORIGIN} ✈️ {DESTINATION}",
                "color": 5763719,  # Green accent color
                "fields": [
                    {"name": "Date", "value": DEPARTURE_DATE, "inline": True},
                    {"name": "Price", "value": f"${message['price']} CAD", "inline": True},
                    {"name": "Flight #", "value": message['flight_number'], "inline": True},
                    {"name": "Duration", "value": str(message['duration']), "inline": True}
                ],
                "footer": {"text": "Air Canada Flight Monitor"},
                "timestamp": datetime.utcnow().isoformat()
            }
        ]
    }
    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
        if response.status_code in [200, 204]:
            print("[+] Discord push notification sent successfully.")
        else:
            print(f"[!] Discord alert failed with status code: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"[!] Error sending Discord alert: {e}")

def send_telegram_notification(message):
    """Sends a text alert to a Telegram chat via Bot API."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    text = (
        f"🚨 *AIR CANADA PRICE DROP ALERT!*\n\n"
        f"✈️ *Route:* {ORIGIN} -> {DESTINATION}\n"
        f"📅 *Date:* {DEPARTURE_DATE}\n"
        f"🔢 *Flight:* {message['flight_number']}\n"
        f"💰 *Price:* ${message['price']} CAD (Under ${PRICE_THRESHOLD_CAD:.2f} target)\n"
    )
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        res_data = response.json()
        if response.status_code == 200 and res_data.get("ok"):
            print("[+] Telegram push notification sent successfully.")
        else:
            print(f"[!] Telegram alert failed: {res_data.get('description')}")
    except requests.exceptions.RequestException as e:
        print(f"[!] Error sending Telegram alert: {e}")

def check_air_canada_prices():
    """Queries Google Flights via SerpApi for Air Canada prices."""
    url = "https://serpapi.com/search"
    params = {
        "engine": "google_flights",
        "departure_id": ORIGIN,
        "arrival_id": DESTINATION,
        "outbound_date": DEPARTURE_DATE,
        "type": "2",
        "travel_class": "1",
        "currency": "CAD",
        "include_airlines": AIRLINE_CODE,
		"outbound_times": "8,17",
        "api_key": SERPAPI_KEY
    }

    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()

        matching_flights = []
        all_flight_groups = data.get("best_flights", []) + data.get("other_flights", [])

        for group in all_flight_groups:
            price = group.get("price")
            flights_info = group.get("flights", [])

            is_air_canada = all(
                flight.get("airline") == "Air Canada" or "AC" in flight.get("airline_logo", "")
                for flight in flights_info
            )

            if is_air_canada and price and price < PRICE_THRESHOLD_CAD:
                flight_details = flights_info[0] if flights_info else {}
                matching_flights.append({
                    "price": price,
                    "flight_number": flight_details.get("flight_number", "N/A"),
                    "departure_time": flight_details.get("departure_token", "N/A"),
                    "duration": group.get("total_duration", "N/A"),
                    "airline": flight_details.get("airline", "Air Canada")
                })

        return matching_flights

    except requests.exceptions.RequestException as e:
        print(f"[!] API Request error: {e}")
        return []

def notify(flight):
    """Prints terminal output and dispatches enabled push notifications."""
    print(f"\n[!] MATCH FOUND: Flight {flight['flight_number']} at ${flight['price']} CAD")

    if ENABLE_DISCORD:
        send_discord_notification(flight)

    if ENABLE_TELEGRAM:
        send_telegram_notification(flight)

def run():
    print(f"[*] Starting Air Canada price tracker for {ORIGIN} -> {DESTINATION} on {DEPARTURE_DATE}...")
    print(f"[*] Target threshold: < ${PRICE_THRESHOLD_CAD} CAD")

    seen_deals = set()

    while True:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] Checking flight prices...")

        deals = check_air_canada_prices()

        if deals:
            for flight in deals:
                deal_key = (flight["flight_number"], flight["price"])
                # Only notify once per unique price/flight combination to avoid notification spam
                if deal_key not in seen_deals:
                    notify(flight)
                    seen_deals.add(deal_key)
        else:
            print("[-] No flights found below the target threshold.")

        time.sleep(POLL_INTERVAL_SECONDS)

if __name__ == "__main__":
    run()