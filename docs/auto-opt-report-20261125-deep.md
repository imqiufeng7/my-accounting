# my-accounting 深度審查報告（2026-11-25）

- 分支：`auto-opt/20261125-deep-accounting-hardening`（以 `master` @ `fd1b2cd` 為基底）
- 修改：10 個獨立 commit，新增 33 個 unittest 測試（原本沒有任何測試）
- 未動：部署設定（`wsgi.py`、`DEPLOY.md` 內的 WSGI 範例）、環境變數檔、CI、資料檔

---

## ⚠️ 需要你立刻處理：`.env.example` 疑似含真實密碼

`.env.example` 第 1、2 行（commit `fd1b2cd`「Update example environment variables」）把原本的佔位字串換成了看起來像真實使用的 `APP_PASSWORD` 與 `FLASK_SECRET_KEY`。這個檔案**有被 Git 追蹤**，已推送到 GitHub。

- 依規定本報告不重述其值，也沒有修改該檔（改它會讓 diff 再次出現這些值）。
- 建議：**如果這就是 PythonAnywhere 上正在用的密碼／金鑰，請立即更換**（WSGI 檔裡的 `os.environ[...]`），再把 `.env.example` 改回 `change-this-password` 之類的佔位字串。單純刪除不夠，它已存在 Git 歷史中；儲存庫若曾公開或分享，需視為外洩。
- 更換 `FLASK_SECRET_KEY` 會讓所有既有登入 session 失效（需重新登入），這是預期行為。

---

## 階段 A：模組地圖

| 模組 | 檔案 | 行數（約） | 用途 |
|---|---|---|---|
| 路由主程式 | `app.py` | 350 | Flask 路由：登入、總覽、三種記帳模式、批次、旅遊結算與分享、股票、帳戶、設定 |
| 設定 | `config.py`、`.env.example`、`requirements.txt` | 55 | 欄位定義、檔案路徑、密碼與 secret key 讀取 |
| WSGI 入口 | `wsgi.py` | 14 | PythonAnywhere 進入點 |
| 儲存層 | `ledger/storage.py` | 85 | CSV 讀寫、原子寫入、以 id 或鍵欄位編輯／刪除 |
| 彙整 | `ledger/aggregator.py` | 147 | 總帳合併、幣別換算、帳戶餘額、股票持股與市值 |
| 分帳 | `ledger/settlement.py` | 74 | 分攤語法解析、淨結餘、債務簡化 |
| 驗證 | `ledger/auth.py` | 37 | 密碼比對、旅遊分享 token |
| 偏好設定 | `ledger/preferences.py` | 19 | `settings.json` 讀寫 |
| 樣板 | `templates/*.html`（11 個） | 700 | Jinja2 頁面 |
| 前端 | `static/js/app.js`、`static/css/style.css` | 260 | 批次列新增／移除、RWD 樣式 |
| 文件 | `README.md`、`DEPLOY.md` | 105 | 使用與部署說明 |
| 舊版封存 | `archive/legacy/*`、`archive/test*.txt` | 300 | 已停用的 CLI 版本與空白測試檔 |

## 階段 B：逐模組審查紀錄

以下檔案都完整讀過（不是抽樣）。行號是指 `master` 上的原始位置。

### app.py
| 嚴重度 | 問題 | 位置 | 處理 |
|---|---|---|---|
| 高 | 開放式重新導向：登入後直接 `redirect(request.args["next"])`，`/login?next=//evil.example` 可用來釣魚 | 33 | ✅ 已修 |
| 高 | 沒有 CSRF 防護：刪紀錄、刪帳戶、改設定、登出等 12 個 POST 表單都可以被惡意網站偷偷送出 | 全檔 | ✅ 已修 |
| 中 | 預設日期用 `date.today()`（伺服器時區）；PythonAnywhere 是 UTC，台灣 00:00～08:00 會變前一天 | 93,125,152,248,266,290,322 | ✅ 已修 |
| 中 | `/accounts/<name>/delete` 用預設轉換器，名稱含 `/` 的帳戶刪不掉（404） | 326 | ✅ 已修 |
| 低 | 表單轉資料列的程式重複 4 次；`stock_edit` 漏了匯率預設 1 | 69-73,103-105,237-239,260 | ✅ 已修（重構） |
| 低 | 金額、股數、匯率等數字欄位後端沒有驗證，非數字會被 `to_float` 默默算成 0 | 69-73 | 建議（見下方） |
| 低 | 登入沒有速率限制，可暴力嘗試密碼 | 27-35 | 建議 |
| 低 | 登入成功沒有輪替 session（session fixation 在 Flask 簽章 cookie 下風險很低） | 32 | 建議 |
| 資訊 | `app.run(debug=True)` 只在本機直接執行時才生效，PythonAnywhere 走 WSGI 不受影響 | 352 | 不動 |

### ledger/auth.py
| 嚴重度 | 問題 | 位置 | 處理 |
|---|---|---|---|
| 中 | `secrets.compare_digest` 遇到非 ASCII 字串丟 `TypeError`，輸入中文密碼 → 登入頁 500；若把密碼設成中文則永遠無法登入 | 12 | ✅ 已修 |
| 低 | 分享 token 無法撤銷、沒有到期日 | 15-29 | 建議 |
| 低 | `get_or_create_share_token` 先查後建，兩個請求同時按可能產生兩個 token（兩個都可用，不影響資料） | 15-29 | 記錄 |

### ledger/settlement.py
| 嚴重度 | 問題 | 位置 | 處理 |
|---|---|---|---|
| 中 | 分攤四捨五入錯誤：先用「未四捨五入的值」算差額（幾乎都是 0）再逐筆四捨五入，100 元三人分只分出 99.99，付款人憑空多 0.01 應收、淨結餘總和不為 0 | 26-34 | ✅ 已修 |
| 中 | 權重寫錯（`Alice:abc`）直接 `float()` 丟例外 → 結算頁與**免登入分享頁**整頁 500；`nan`/`inf`/負數會算出 NaN 或負分攤 | 18 | ✅ 已修 |
| 低 | `":2"`（沒有名字）會產生名字為空字串的分攤對象 | 16-18 | 記錄 |

### ledger/storage.py
| 嚴重度 | 問題 | 位置 | 處理 |
|---|---|---|---|
| 高 | 併發寫入遺失資料：所有寫入都是「讀整檔→改→寫回」且沒有鎖。實測 8 執行緒×25 筆只留下約 30 筆；4 行程×25 筆只留下約 30 筆 | 30-84 | ✅ 已修 |
| 資訊 | `_atomic_write` 已用暫存檔＋`os.replace`，檔案本身不會寫壞 | 20-27 | 保留 |

### ledger/preferences.py
| 嚴重度 | 問題 | 位置 | 處理 |
|---|---|---|---|
| 中 | `settings.json` 損毀（或內容不是物件）就丟例外，而每個記帳頁都會讀設定 → 全站記帳頁 500；寫入又不是原子寫入，中斷就會損毀 | 7-19 | ✅ 已修 |

### ledger/aggregator.py
| 嚴重度 | 問題 | 位置 | 處理 |
|---|---|---|---|
| 低 | 帳戶餘額以 `日期 >= 期初日期` 計入支出：若期初餘額是「當天結束時」對帳的數字，當天的支出會被重複扣掉。語意要由你決定 | 116,121 | 建議（未動） |
| 低 | 旅遊紀錄只要「付款方式」是你的帳戶就整筆扣款，與「付款人」是誰無關；朋友代墊、但誤選你的帳戶時餘額會錯 | 113-117 | 記錄 |
| 低 | 日期用字串比較，依賴 `YYYY-MM-DD` 格式（目前表單都是 `type=date`，正常） | 116 | 記錄 |
| 資訊 | 浮點數計算金額；個人記帳金額規模下誤差可忽略，顯示時都有四捨五入 | 全檔 | 記錄 |

### config.py / .env.example / wsgi.py
| 嚴重度 | 問題 | 位置 | 處理 |
|---|---|---|---|
| 高 | `.env.example` 疑似含真實密碼與金鑰（見最上方） | `.env.example`:1-2 | 只報告，建議輪替 |
| 中 | 未設環境變數時預設密碼 `changeme`、secret key `dev-secret-key-change-me`，部署漏設就等於公開 | `config.py`:9-10 | 建議（屬環境設定，未動） |
| 低 | 沒有設定 `SESSION_COOKIE_SECURE`，HTTPS 站台建議開啟 | `config.py` | 建議（會影響本機 http 開發，未動） |

### templates/、static/
- 全部 11 個樣板都使用 Jinja2 自動跳脫，沒有 `|safe`、沒有把使用者資料放進 `<script>`，**未發現 XSS**。
- `app.js` 只操作 `<template>` 複製，沒有 `innerHTML`，安全。
- 12 個 POST 表單已補 CSRF 隱藏欄位。

### archive/legacy/
- 已停用的 CLI 程式，`generate_report.py` 有正確用 `html.escape`。`record.csv` 只有 3 筆範例資料。`archive/test1~3.txt` 是空檔。無需修改，可考慮整個移除。

---

## 階段 C：已做的修改（10 個 commit）

| # | Commit | 檔案 | 理由 |
|---|---|---|---|
| 1 | 修正登入後 next 參數的開放式重新導向 | `app.py`、`ledger/auth.py`、`tests/support.py`、`tests/test_login_redirect.py` | 只允許站內相對路徑（擋 `//`、`/\`、`https:`、`javascript:`、控制字元） |
| 2 | 修正輸入中文密碼時登入頁 500 錯誤 | `ledger/auth.py`、`tests/test_auth.py` | 比對 UTF-8 位元組 |
| 3 | 修正旅遊分帳均分時合計少一分錢 | `ledger/settlement.py`、`tests/test_settlement.py` | 以整數「分」分配，差額補給最後一人 |
| 4 | 修正分攤權重寫錯時結算頁與公開分享頁 500 | `ledger/settlement.py`、`tests/test_travel_pages.py` | 無效權重視為 1 |
| 5 | 新增 CSRF 防護 | `app.py`、`ledger/auth.py`、9 個樣板、`tests/test_csrf.py` | session token＋隱藏欄位，失敗回 400 |
| 6 | 修正雲端主機（UTC）下預設日期在台灣清晨變成前一天 | 新增 `ledger/clock.py`；`config.py`、`app.py`、`ledger/auth.py`、`ledger/aggregator.py`、`tests/test_clock.py` | 以 `Asia/Taipei` 計算今天，可用 `APP_TIMEZONE` 覆寫；無時區資料時退回 UTC+8 |
| 7 | 修正同時寫入 CSV 時紀錄遺失（加入檔案鎖） | `ledger/storage.py`、`.gitignore`、`tests/test_storage.py` | `fcntl.flock`（跨行程）＋執行緒鎖；`.gitignore` 補 `data/.*.lock`、`data/.*.tmp` |
| 8 | 修正帳戶名稱含「/」時無法刪除 | `app.py`、`tests/test_accounts.py` | 改用 `<path:name>`；順便補帳戶餘額計算的整合測試 |
| 9 | 修正 settings.json 損毀時所有記帳頁面 500 | `ledger/preferences.py`、`tests/test_preferences.py` | 讀取失敗退回預設值；寫入改原子寫入 |
| 10 | 重構表單轉資料列邏輯，並修正股票編輯時匯率未預設為 1 | `app.py`、`tests/test_forms.py` | 4 處重複程式合併為 `_form_to_row(fields, form)` |

## 階段 D：驗證方式與實際結果

環境：Python 3.11.18，在沙箱外的暫存 venv 只安裝 `requirements.txt` 列的 `Flask>=3.0`（實際 3.1.3）。專案沒有列 pytest，所以測試用標準函式庫 `unittest` 撰寫，執行方式：

```bash
python -m unittest          # 在專案根目錄
```

**最終結果：`Ran 33 tests in 0.569s — OK`**；`python -m compileall app.py config.py wsgi.py ledger tests` 無錯誤。專案沒有 lint／build 設定，所以沒有 lint 可跑。

### 反向驗證（暫時還原修復、保留測試，確認測試會失敗）

| # | 還原的檔案 | 還原後結果 | 恢復後 |
|---|---|---|---|
| 1 | `app.py` | `FAILED (failures=4)`：4 個外部網址都被導出去 | OK |
| 2 | `ledger/auth.py` | `FAILED (errors=2)`：`TypeError: comparing strings with non-ASCII characters` | OK |
| 3 | `ledger/settlement.py` | `FAILED (failures=5)`：`99.99 != 100`、`0.09 != 0.1`、`1234.56 != 1234.57` | OK |
| 4 | `ledger/settlement.py` | `FAILED (failures=1, errors=6)`：`ValueError`，分享頁 500 | OK |
| 5 | `app.py`、`ledger/auth.py`、`templates/` | `FAILED (failures=11, errors=1)`：無 token／偽造 token 的刪除都成功、表單沒有 token | OK |
| 6 | `app.py`、`ledger/auth.py` | `FAILED (failures=5)`：表單預設日期、市價更新日期、分享建立日期都是 UTC 日期 | OK |
| 7 | `ledger/storage.py` | `FAILED (failures=2)`：`32 != 100`、`33 != 200`（連跑 3 次都失敗） | OK（連跑 3 次都通過） |
| 8 | `app.py` | `FAILED (failures=1)`：`404 != 302` | OK |
| 9 | （修復前先跑測試） | `FAILED (errors=3)`：`JSONDecodeError`、`'list' object is not a mapping` | OK |
| 10 | （修復前先跑測試） | `FAILED (failures=1)`：`'' != '1'` | OK |

### 實機冒煙測試（真的啟動 `flask run`，用 curl 走一次）
- 登入頁發出 43 字元 token；不帶 token 登入 → `400`；帶 token、`next=//evil.example` → `302` 到站內 `/`
- 新增一筆東京 100 元、A 付、A,B,C 均分 → 結算頁淨結餘 `66.67 / -33.33 / -33.34`（合計 0，修正前是 `66.67 / -33.33 / -33.33`）
- 產生分享連結 → 正常

### 沒驗到的
- 沒有在真正的 PythonAnywhere 上跑；檔案鎖在 PythonAnywhere 的檔案系統上**預期**可用（一般 Linux 檔案系統都支援 `flock`），但沒有實測。
- 沒有用真實瀏覽器點過頁面（只用 Flask 測試用戶端與 curl）。
- 沒有你的真實 `data/*.csv`（`.gitignore` 排除），所以舊資料遇到新邏輯的表現只用合成資料測過。

## 階段 E：自我複查

用 `git diff master` 把全部修改重讀一遍，確認：
- 所有 `date.today()` 都已替換（`grep` 確認 `app.py`、`ledger/` 已無殘留；`archive/` 是封存程式不動）。
- 12 個 POST 表單全部帶 token，有測試逐頁檢查。
- 檔案鎖的 `with _locked(...)` 包住完整的讀→改→寫；`append_row` 的 `id` 欄位檢查移到鎖外，行為不變。
- 第一次用正規表示式自動縮排 storage 函式時產生錯誤縮排，已發現並改為手寫重寫，再跑完整測試確認。

---

## 會改變既有行為的地方（合併前請決定）

1. **CSRF**：部署後，部署前就開著的頁面第一次送出會得到 400「表單已過期」，重新整理即可。錯誤頁是 Flask 預設樣式（英文標題＋中文說明）。
2. **分帳金額**：既有旅程的淨結餘可能變動 ±0.01（變成正確值）；最後一位分攤者可能多／少 1 分錢。
3. **無效權重**：`Alice:abc`、負數、`nan` 現在視為 1（均分），而不是讓頁面壞掉。如果你偏好「直接在新增時擋下」，需要另外做表單驗證。
4. **日期**：所有「今天」改以台灣時間計算。如果你人在國外想用當地日期，可設環境變數 `APP_TIMEZONE`（例如 `Asia/Tokyo`）。
5. **檔案鎖**：`data/` 目錄會多出 `.xxx.csv.lock` 隱藏檔（已加進 `.gitignore`），刪掉無害。

## 建議但未動手的項目

1. **輪替 `.env.example` 中疑似真實的密碼與金鑰**（最優先，見最上方）。
2. 未設 `APP_PASSWORD`/`FLASK_SECRET_KEY` 時應拒絕啟動，而不是用 `changeme` 預設值（屬環境設定，依規定不動）。
3. PythonAnywhere 是 HTTPS，可在 WSGI 檔加 `app.config["SESSION_COOKIE_SECURE"] = True`。
4. 登入加簡單速率限制（例如同 IP 每分鐘 5 次）。
5. 後端驗證金額／股數／匯率必須是數字，錯誤時顯示訊息而不是默默算 0。
6. 分享連結增加「撤銷」功能與到期日。
7. 釐清「期初日期當天的支出要不要扣」的語意，必要時改成 `>`。
8. 匯出 CSV 時防範公式注入（以 `=`、`+`、`-`、`@` 開頭的欄位），若之後會用 Excel 開資料檔。
9. 移除 `archive/test1~3.txt` 空檔。

## 沒有審查到的範圍

- `static/css/style.css`（238 行）只快速瀏覽，未逐條檢查樣式與 RWD 細節。
- `archive/legacy/report.html` 是產出的靜態報表，只看了開頭。
- 沒有做無障礙或瀏覽器相容性檢查。
- 沒有審查 PythonAnywhere 端實際的 WSGI 檔與伺服器設定（不在儲存庫內）。

## 如何採用

```bash
git fetch origin auto-opt/20261125-deep-accounting-hardening
git checkout auto-opt/20261125-deep-accounting-hardening
python -m unittest          # 應顯示 Ran 33 tests ... OK
```

確認沒問題後再自行合併進 `master`，然後在 PythonAnywhere 上 `git pull` 並按 Reload。各 commit 彼此獨立，不想要的可以 `git revert` 單獨拿掉（第 5 項 CSRF 修改了 `tests/support.py` 的登入輔助函式，後續測試依賴它）。
