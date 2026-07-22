import csv
import os

CSV_FILE = "record.csv"
FIELDS = ["日期", "類別", "支出項目", "金額"]


def ensure_csv_header():
    file_exists = os.path.isfile(CSV_FILE)
    if not file_exists:
        with open(CSV_FILE, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(FIELDS)


def add_record(date, category, item, amount):
    with open(CSV_FILE, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow([date, category, item, amount])


def main():
    ensure_csv_header()
    print("記帳程式（直接按 Enter 不輸入日期即可結束）")

    while True:
        date = input("日期：").strip()
        if date == "":
            print("結束記帳，資料已儲存至 record.csv")
            break

        category = input("類別：").strip()
        item = input("支出項目：").strip()

        while True:
            amount_str = input("金額：").strip()
            try:
                amount = float(amount_str)
                break
            except ValueError:
                print("請輸入有效的數字金額")

        add_record(date, category, item, amount)
        print(f"已新增：{date} | {category} | {item} | {amount}")
        print("-" * 30)


if __name__ == "__main__":
    main()
