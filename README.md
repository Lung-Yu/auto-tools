# auto-tools

自動化工具集，目前收錄台鐵訂票可用性查詢腳本。

---

## 台鐵訂票查詢 `check_train.py`

自動查詢台鐵指定路線、日期的可售車次，有票時發送 macOS 通知。

### 功能

- 查詢指定日期的可售車次（列車類型、出發/抵達時間、票價）
- 支援一次查多個日期
- 支援指定購買座位數（自動過濾無法滿足數量的車次）
- 支援持續輪詢模式，有票立即彈出 macOS 通知
- 通知訊息含日期、車次號碼與出發時間

### 環境需求

- Python 3.9+
- macOS（通知功能依賴 `osascript`）

### 安裝

```bash
python3 -m venv venv
venv/bin/pip install requests beautifulsoup4 lxml
```

### 設定

編輯 `check_train.py` 頂部的變數：

```python
START_STATION = "2220-清水"   # 出發站（格式：站碼-站名）
END_STATION   = "1000-臺北"   # 抵達站
PID           = "A123456789"  # 身分證字號（用於送出查詢表單）
TARGET_DATES  = ["2026/02/21", "2026/02/22", "2026/02/23"]  # 預設查詢日期
```

> 常用站碼：臺北 `1000`、板橋 `1020`、臺中 `3300`、清水 `2220`、嘉義 `4080`、臺南 `4220`、高雄 `4400`

### 使用方式

```bash
# 單次查詢（使用預設日期）
venv/bin/python3 check_train.py

# 指定日期
venv/bin/python3 check_train.py --dates 2026/02/22 2026/02/23

# 查詢 2 張座位
venv/bin/python3 check_train.py --qty 2

# 每 60 秒持續查詢，有票即通知
venv/bin/python3 check_train.py --loop

# 自訂間隔（秒）
venv/bin/python3 check_train.py --loop --interval 120

# 組合使用
venv/bin/python3 check_train.py --dates 2026/02/22 2026/02/23 --qty 2 --loop --interval 90
```

### 參數說明

| 參數 | 說明 | 預設值 |
|------|------|--------|
| `--dates` | 查詢日期，可多個（空白分隔） | 腳本內 `TARGET_DATES` |
| `--qty` | 座位數 | `1` |
| `--loop` | 持續輪詢模式 | 否 |
| `--interval` | 輪詢間隔秒數（需搭配 `--loop`） | `60` |

### 輸出範例

```
==============================================================
  台鐵 Availability Checker  |  2026-02-20 08:16:36
  Route : 清水 → 臺北  (x1 座位)
  Dates : 2026/02/21, 2026/02/22, 2026/02/23
==============================================================

  [2026/02/21]  ✗ No trains / no seats found

  [2026/02/22]  ✗ No trains / no seats found

  [2026/02/23]  ✓ 6 train(s) available:
    車次  3000  自強    07:10 → 09:27  $493
    車次   112  自強    09:35 → 12:07  $493
    車次   510  莒光    11:46 → 14:36  $380
    車次   516  莒光    14:32 → 17:18  $380
    車次   130  自強    16:20 → 18:51  $493
    車次   554  莒光    17:50 → 21:02  $380

  *** TICKETS AVAILABLE — book now! ***
```
