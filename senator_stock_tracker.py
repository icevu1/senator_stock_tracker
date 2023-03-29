import time
import requests
import base64
import os
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



def fetch_data(url):
    response = requests.get(url)
    if response.status_code == 200:
        return response.text
    else:
        print("Error fetching data from the website")
        return None

def parse_newest_trade(html):
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("tbody")
    newest_row = table.find("tr")

    trade_size = newest_row.find("span", class_="q-field trade-size")
    trade_price = newest_row.find("span", class_="q-field trade-price")
    politician_name = newest_row.find("h3", class_="q-fieldset politician-name").find("a")
    issuer_name = newest_row.find("h3", class_="q-fieldset issuer-name").find("a")
    def is_trade_type(tag):
        return tag.has_attr("class") and "q-field" in tag["class"] and "tx-type" in tag["class"]

    trade_type = newest_row.find_all(is_trade_type)[0]

    if "tx-type--buy" in trade_type["class"]:
        trade_type_text = "Buy"
    else:
        trade_type_text = "Sell"


    #trade = (politician_name.text, issuer_name.text, trade_size.text, trade_price.text,  trade_type_text)
    trade = (
        politician_name.text if politician_name else "",
        issuer_name.text if issuer_name else "",
        trade_size.text if trade_size else "",
        trade_price.text if trade_price else "",
        trade_type_text if trade_type else "")
    return trade

def send_email(credentials, trade):
    msg = EmailMessage()
    msg.set_content(f"Senator's name: {trade[0]}\nIssuer: {trade[1]}\nTrade size: {trade[2]}$\nPrice: {trade[3]}$/Share \nType: {trade[4]}")

    msg["Subject"] = f"New Trade Alert: {trade[0]} | {trade[1]} | {trade[4].capitalize()} | Size: {trade[2]} | Price: {trade[3]}"

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
    previous_trade = None
    credentials = get_credentials()

    while True:
        html = fetch_data(URL)
        if html:
            current_trade = parse_newest_trade(html)

            if previous_trade != current_trade:
                print(f"New trade added: Senator's name: {current_trade[0]} Issuer: {current_trade[1]} Trade size: {current_trade[2]} Price: {current_trade[3]} Type: {current_trade[4]}")
                send_email(credentials, current_trade)

            previous_trade = current_trade

        time.sleep(WATCH_INTERVAL)

if __name__ == "__main__":
    monitor_trades()