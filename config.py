import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

BASE_CURRENCY = "TWD"

# 「今天」的判定時區（表單預設日期、市價更新日期、分享連結建立日期都用它）
TIMEZONE = os.environ.get("APP_TIMEZONE", "Asia/Taipei")

APP_PASSWORD = os.environ.get("APP_PASSWORD", "changeme")
FLASK_SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key-change-me")

# Shared field set for expense-style modes (personal / work / travel).
# "id" must stay first: ledger.storage relies on it to target rows for edit/delete.
EXPENSE_FIELDS = ["id", "日期", "類別", "項目", "金額", "幣別", "匯率", "付款人", "付款方式", "地點", "備註"]

MODE_CONFIG = {
    "personal": {
        "label": "個人",
        "file": DATA_DIR / "personal.csv",
        "fields": EXPENSE_FIELDS,
        "has_destination": False,
        "has_shares": False,
    },
    "work": {
        "label": "工作",
        "file": DATA_DIR / "work.csv",
        "fields": EXPENSE_FIELDS,
        "has_destination": False,
        "has_shares": False,
    },
    "travel": {
        "label": "旅遊",
        "file": DATA_DIR / "travel.csv",
        "fields": ["id", "目的地"] + EXPENSE_FIELDS[1:] + ["分攤對象"],
        "has_destination": True,
        "has_shares": True,
    },
}

STOCK_FIELDS = ["id", "日期", "股票代號", "交易類型", "股數", "單價", "手續費", "幣別", "匯率", "付款方式", "備註"]
STOCK_FILE = DATA_DIR / "stock.csv"
STOCK_PRICES_FILE = DATA_DIR / "stock_prices.csv"
STOCK_PRICES_FIELDS = ["股票代號", "目前市價", "幣別", "匯率", "更新日期"]

ACCOUNTS_FILE = DATA_DIR / "accounts.csv"
ACCOUNTS_FIELDS = ["帳戶名稱", "類型", "期初餘額", "幣別", "匯率", "期初日期", "備註"]

TRAVEL_SHARES_FILE = DATA_DIR / "travel_shares.csv"
TRAVEL_SHARES_FIELDS = ["token", "目的地", "建立日期"]

SETTINGS_FILE = DATA_DIR / "settings.json"
DEFAULT_SETTINGS = {"預設付款人": "", "預設付款方式": ""}
