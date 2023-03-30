import time
import requests
import base64
import os
import json
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from email.message import EmailMessage

URL = "https://www.capitoltrades.com/trades"
WATCH_INTERVAL = 60  # in seconds

load_dotenv()

# Email settings
TO_EMAIL = os.getenv("TO_EMAIL")
CLIENT_SECRET_FILE = os.getenv("CLIENT_SECRET_FILE")
SCOPES = ["https://www.googleapis.com/auth/gmail.send"]


def save_previous_trades(trades, file_path='previous_trades.json'):
    with open(file_path, 'w') as f:
        json.dump(trades, f)

def load_previous_trades(file_path='previous_trades.json'):
    if not os.path.exists(file_path):
        return []
    with open(file_path, 'r') as f:
        return json.load(f)

def fetch_data(url):
    response = requests.get(url)
    if response.status_code == 200:
        return response.text
    else:
        print("Error fetching data from the website")
        return None

def parse_trades(html):
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("tbody")
    rows = table.find_all("tr")

    trades = []

    for row in rows:
        trade_size = row.find("span", class_="q-field trade-size")
        trade_price = row.find("span", class_="q-field trade-price")
        politician_name = row.find("h3", class_="q-fieldset politician-name").find("a")
        issuer_name = row.find("h3", class_="q-fieldset issuer-name").find("a")

        if not all([trade_size, trade_price, politician_name, issuer_name]):
            continue

        def is_trade_type(tag):
            return tag.has_attr("class") and "q-field" in tag["class"] and "tx-type" in tag["class"]

        trade_type = row.find_all(is_trade_type)[0]

        if "tx-type--buy" in trade_type["class"]:
            trade_type_text = "Buy"
        else:
            trade_type_text = "Sell"

        trade_id = f"{politician_name.text}-{issuer_name.text}-{trade_size.text}-{trade_price.text}-{trade_type_text}"
        trade = {
            "id": trade_id,
            "politician_name": politician_name.text,
            "issuer_name": issuer_name.text,
            "trade_size": trade_size.text,
            "trade_price": trade_price.text,
            "trade_type": trade_type_text,
        }

        trades.append(trade)

    return trades


def send_email(credentials, trade):
    msg = EmailMessage()
    msg.set_content(f"Senator's name: {trade['politician_name']}\nIssuer: {trade['issuer_name']}\nTrade size: {trade['trade_size']}$\nPrice: {trade['trade_price']}$\nType: {trade['trade_type']}")

    msg["Subject"] = f"New Trade Alert: {trade['politician_name']} | {trade['issuer_name']} | {trade['trade_type'].capitalize()} | Size: {trade['trade_size']} | Price: {trade['trade_price']}"

    msg["To"] = TO_EMAIL

    raw_msg = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")

    service = build("gmail", "v1", credentials=credentials)
    service.users().messages().send(userId="me", body={"raw": raw_msg}).execute()


def get_credentials():
    SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
    creds = None

    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    return creds

def monitor_trades():
    credentials = get_credentials()

    previous_trades_file = "previous_trades.json"
    previous_trades = load_previous_trades(previous_trades_file)

    if previous_trades:
        last_trade_id = previous_trades[0]["id"]
    else:
        last_trade_id = None

    while True:
        html = fetch_data(URL)
        if html:
            current_trades = parse_trades(html)

            new_trades = []
            for trade in current_trades:
                if trade["id"] == last_trade_id:
                    break
                new_trades.append(trade)

            if new_trades:
                last_trade_id = new_trades[0]["id"]
                previous_trades = new_trades + previous_trades
                save_previous_trades(previous_trades, previous_trades_file)

                for trade in reversed(new_trades):
                    print(f"New trade added: {trade}")
                    send_email(credentials, trade)

        time.sleep(WATCH_INTERVAL)

if __name__ == "__main__":
    monitor_trades()