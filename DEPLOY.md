# 部署到 PythonAnywhere（手機隨處記帳）

這份文件說明如何把這個 Flask 記帳程式部署到 [PythonAnywhere](https://www.pythonanywhere.com/) 免費方案，讓手機在任何地方（不需要跟電腦同一個 Wi-Fi）都能連線記帳，也能把旅遊分帳連結分享給朋友。

## 一次性設定

1. **註冊帳號**：到 pythonanywhere.com 註冊一個免費帳號（Beginner 方案即可）。
2. **上傳程式碼**：登入後開啟一個 Bash console，執行：
   ```bash
   git clone <你的 GitHub repo 網址> my-accounting
   cd my-accounting
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
3. **設定環境變數**：在同一個目錄建立 `.env`（可以複製 `.env.example` 再修改）：
   ```bash
   cp .env.example .env
   nano .env   # 把 APP_PASSWORD 改成你自己的密碼，FLASK_SECRET_KEY 改成一串隨機字串
   ```
   PythonAnywhere 的 WSGI 檔案不會自動讀取 `.env`，所以要在 WSGI 設定檔裡手動 `import os; os.environ["APP_PASSWORD"] = "..."`（見下一步），或使用 PythonAnywhere 的環境變數功能（付費方案才有），Beginner 方案建議直接寫在 WSGI 檔案裡（見下方範例）。
4. **建立 Web App**：到 PythonAnywhere 網站的 **Web** 頁籤 → **Add a new web app** → 選 **Flask** → 選 Python 版本。
5. **設定虛擬環境路徑**：在 Web 頁籤的 "Virtualenv" 欄位填入 `/home/你的帳號/my-accounting/venv`。
6. **編輯 WSGI 設定檔**：點開 Web 頁籤提供的 WSGI configuration file 連結，清空內容後貼上：
   ```python
   import os
   import sys

   path = "/home/你的帳號/my-accounting"
   if path not in sys.path:
       sys.path.insert(0, path)

   os.environ["APP_PASSWORD"] = "你的密碼"
   os.environ["FLASK_SECRET_KEY"] = "一串隨機字串"

   from app import app as application
   ```
7. 按 **Reload** 讓網頁生效。網址會是 `https://你的帳號.pythonanywhere.com`，手機直接開這個網址就能記帳。

## 之後更新程式碼

每次在本機或 GitHub 上更新程式碼後：
```bash
# 在 PythonAnywhere 的 Bash console
cd my-accounting
git pull
source venv/bin/activate
pip install -r requirements.txt   # 只有 requirements.txt 有變動時才需要
```
接著回到 Web 頁籤按 **Reload**。

## 注意事項

- `data/` 目錄下的 CSV 就是所有記帳資料，存在 PythonAnywhere 帳號的個人檔案系統中，重新部署不會遺失。**建議定期備份**（例如用 Bash console 把 `data/` 打包下載）。
- 記帳主功能有密碼保護（`APP_PASSWORD`），請不要把 `.env` 或密碼提交進 GitHub（`.gitignore` 已排除 `.env`）。
- 旅遊分帳分享連結（`/share/travel/<token>`）刻意不需要密碼，方便直接傳給朋友，但也代表任何拿到連結的人都能看到該趟旅程的明細，請只分享給信任的人。
