# my-accounting

一個多模式的個人記帳網頁應用（Flask）。可依情境切換「個人／工作／旅遊／股票」四種模式記帳，最終彙整成總帳並計算總資產，供核對銀行帳戶餘額；旅遊模式支援分帳結算，並可產生免登入的分享連結給同行朋友即時查看。

## 功能

- **多模式記帳**：個人、工作、旅遊、股票各自獨立的資料檔，彙整到共同的總帳與總資產計算。
- **單筆記帳 / 單日批次記帳**：花費當下記一筆，或一天結束時批次記錄（共用日期/類別/付款方式，只需分別輸入項目與金額）。
- **欄位預設值**：可在「設定」頁面指定預設付款人、預設付款方式，新增記帳時自動帶入（日期一律預設今天）。
- **帳戶與總資產核對**：在「帳戶」頁面登記各帳戶的期初餘額，系統會扣除後續支出（含股票買賣的現金流），算出目前餘額與總資產，供你和銀行 App 核對；核對後可更新期初餘額作為新的校正基準。
- **股票模式**：記錄買賣交易，市價於「股票市價」頁面手動更新，計算目前市值與損益。
- **旅遊分帳**：以「目的地」為一趟旅程的單位，記錄付款人與分攤對象（均分或依權重），自動計算每人淨結餘與最少轉帳次數的還款建議。
- **旅遊分享連結**：針對指定旅程產生免登入的唯讀連結，分享給朋友後資料會即時同步更新，不是凍結快照。
- **密碼保護**：主功能（新增/編輯/查看總資產）需要輸入共用密碼；分享連結不需要。
- **RWD 手機版面**：可搭配 [DEPLOY.md](DEPLOY.md) 部署到 PythonAnywhere 免費方案，手機隨時隨地都能記帳與查看分享頁。

## 檔案結構

| 路徑 | 說明 |
|---|---|
| `app.py` | Flask 路由與主程式 |
| `wsgi.py` | PythonAnywhere WSGI 進入點 |
| `config.py` | 模式設定、欄位定義、常數 |
| `ledger/storage.py` | CSV 讀寫（新增/編輯/刪除，原子寫入） |
| `ledger/aggregator.py` | 總帳彙整、幣別換算、總資產計算 |
| `ledger/settlement.py` | 分攤解析、debt-simplification 分帳演算法 |
| `ledger/auth.py` | 密碼登入、旅遊分享連結 token |
| `ledger/preferences.py` | 使用者預設值（設定頁） |
| `data/*.csv` | 各模式的記帳資料 |
| `templates/`, `static/` | 網頁樣板與樣式 |
| `archive/legacy/` | 舊版 CLI 記帳程式（`accounting.py`、`generate_report.py`），已停用保留備查 |

## 本機執行

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env   # 修改 APP_PASSWORD、FLASK_SECRET_KEY
export $(cat .env | xargs)

python3 app.py
```
開啟 http://127.0.0.1:5000，輸入 `.env` 裡設定的密碼登入即可開始記帳。

## 部署到雲端（手機隨處記帳）

見 [DEPLOY.md](DEPLOY.md)：把程式碼放上 GitHub，部署到 PythonAnywhere 免費方案，取得一個手機隨時能連線的網址。
