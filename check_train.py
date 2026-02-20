#!/usr/bin/env python3
"""
Taiwan Railway (台鐵) Train Availability Checker - Windows Compatible
Target: 清水 → 臺北, dates: 2026/02/20, 2026/02/21, 2026/02/22
"""

import re
import sys
import time
import subprocess
from datetime import datetime

import requests
from bs4 import BeautifulSoup

# --- Windows 通知支援 ---
try:
    from plyer import notification
    HAS_NOTIFY = True
except ImportError:
    HAS_NOTIFY = False

BASE_URL = "https://www.railway.gov.tw"
QUERY_PAGE = f"{BASE_URL}/tra-tip-web/tip/tip001/tip123/query"
QUERY_TRAIN = f"{BASE_URL}/tra-tip-web/tip/tip001/tip123/queryTrain"

START_STATION = "2220-清水"
END_STATION   = "1000-臺北"
PID           = "A115743862"
NORMAL_QTY    = "1"

TARGET_DATES = ["2026/02/21", "2026/02/22", "2026/02/23"]

TIME_WINDOWS = [
    ("06:00", "14:00"),
    ("14:00", "22:00"),
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
    "Origin": BASE_URL,
    "Referer": QUERY_PAGE,
    "Upgrade-Insecure-Requests": "1",
}

def win_notify(title, message):
    """Windows 原生通知 (取代 Mac 的 osascript)"""
    print(f"\n[通知] {title}: {message}")
    if HAS_NOTIFY:
        try:
            notification.notify(
                title=title,
                message=message,
                app_name="台鐵訂票助手",
                timeout=10
            )
        except Exception:
            pass
    else:
        # 如果沒安裝 plyer，就發出系統嗶聲作為提醒
        import ctypes
        ctypes.windll.user32.MessageBeep(0)

def get_form_tokens(session):
    resp = session.get(QUERY_PAGE, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    # 自動適配解析器
    parser = "lxml" if "lxml" in sys.modules else "html.parser"
    soup = BeautifulSoup(resp.text, parser)
    form = soup.find("form", id="queryForm")
    if not form:
        raise RuntimeError("queryForm not found")
    csrf   = form.find("input", {"name": "_csrf"})
    token  = form.find("input", {"name": "completeToken"})
    return (
        csrf["value"]  if csrf  else "",
        token["value"] if token else "",
    )

def build_form_data(csrf, complete_token, ride_date, start_time, end_time):
    train_types = ["11", "1", "2", "3", "4", "5"]
    data = [
        ("_csrf",                                      csrf),
        ("custIdTypeEnum",                             "PERSON_ID"),
        ("pid",                                        PID),
        ("tripType",                                   "ONEWAY"),
        ("orderType",                                  "BY_TIME"),
        ("ticketOrderParamList[0].tripNo",             "TRIP1"),
        ("ticketOrderParamList[0].startStation",       START_STATION),
        ("ticketOrderParamList[0].endStation",         END_STATION),
        ("ticketOrderParamList[0].rideDate",           ride_date),
        ("ticketOrderParamList[0].startOrEndTime",     "true"),
        ("ticketOrderParamList[0].startTime",          start_time),
        ("ticketOrderParamList[0].endTime",            end_time),
        ("ticketOrderParamList[0].normalQty",          NORMAL_QTY),
        ("ticketOrderParamList[0].wheelChairQty",      "0"),
        ("ticketOrderParamList[0].parentChildQty",     "0"),
        ("ticketOrderParamList[0].trainNoList[0]",     ""),
        ("ticketOrderParamList[0].trainNoList[1]",     ""),
        ("ticketOrderParamList[0].trainNoList[2]",     ""),
    ]
    for t in train_types:
        data.append(("ticketOrderParamList[0].trainTypeList", t))
    data += [
        ("ticketOrderParamList[0].chgSeat",  "true"),
        ("ticketOrderParamList[0].seatPref", "NONE"),
        ("completeToken",                    complete_token),
    ]
    return data

def parse_trains(html):
    # 自動適配解析器
    parser = "lxml" if "lxml" in sys.modules else "html.parser"
    soup = BeautifulSoup(html, parser)
    result = {"available": [], "sold_out": [], "no_seats_msg": False, "error_msgs": []}

    page_text = soup.get_text(" ", strip=True)
    no_seat_keywords = ["均沒有空位", "查無可售座位", "無座位", "候補"]
    result["no_seats_msg"] = any(k in page_text for k in no_seat_keywords)

    skip_keywords = ["官方網站", "護照號碼", "未享法定", "切勿使用", "v3 驗證"]
    for tag in soup.find_all(class_=lambda c: c and any(x in (c if isinstance(c, str) else " ".join(c)) for x in ["mag-error", "mag-info", "alert-info"])):
        txt = tag.get_text(strip=True)
        if txt and not any(k in txt for k in skip_keywords):
            result["error_msgs"].append(txt)

    rows = soup.find_all("tr")
    for row in rows:
        cells = row.find_all("td")
        if len(cells) < 4:
            continue
        row_text = "|".join(c.get_text(strip=True) for c in cells)

        if not re.search(r'\d{2}:\d{2}', row_text):
            continue

        is_available = "選擇" in row_text
        is_sold_out  = any(k in row_text for k in ["售完", "額滿", "無座", "候補"])

        if not (is_available or is_sold_out):
            continue

        train_no_m = re.search(r'\b(\d{3,5})\b', row_text)
        train_no   = train_no_m.group(1) if train_no_m else "?"

        times = re.findall(r'\d{2}:\d{2}', row_text)
        dep = times[0] if len(times) > 0 else "?"
        arr = times[1] if len(times) > 1 else "?"

        price_m = re.search(r'(\d{3,4})\s*元', row_text)
        price   = price_m.group(1) if price_m else "?"

        type_m = re.search(r'(自強|莒光|復興|區間|普快|太魯閣|普悠瑪|城際)', row_text)
        train_type = type_m.group(1) if type_m else ""

        entry = {
            "no":    train_no,
            "type":  train_type,
            "dep":   dep,
            "arr":   arr,
            "price": price,
            "raw":   row_text[:120],
        }

        if is_available:
            result["available"].append(entry)
        else:
            result["sold_out"].append(entry)

    return result

def check_window(session, ride_date, start_time, end_time):
    csrf, complete_token = get_form_tokens(session)
    form_data = build_form_data(csrf, complete_token, ride_date, start_time, end_time)
    resp = session.post(
        QUERY_TRAIN,
        data=form_data,
        headers={**HEADERS, "Content-Type": "application/x-www-form-urlencoded"},
        timeout=20,
        allow_redirects=True,
    )
    resp.raise_for_status()
    return parse_trains(resp.text)

def check_date(session, ride_date):
    all_available = []
    all_sold_out  = []
    
    for (t0, t1) in TIME_WINDOWS:
        try:
            r = check_window(session, ride_date, t0, t1)
            all_available.extend(r["available"])
            all_sold_out.extend(r["sold_out"])
        except Exception as e:
            print(f"    [ERR {t0}-{t1}] {e}")
        time.sleep(1.5)

    seen = set()
    unique_available = []
    for t in all_available:
        if t["no"] not in seen:
            seen.add(t["no"])
            unique_available.append(t)

    return unique_available, all_sold_out

def run_once():
    session = requests.Session()
    any_avail = False

    print(f"\n{'='*62}")
    print(f"  台鐵 Availability Checker | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    start_name = START_STATION.split("-", 1)[-1]
    end_name   = END_STATION.split("-", 1)[-1]
    print(f"  Route : {start_name} → {end_name}  (x{NORMAL_QTY} 座位)")
    print(f"  Dates : {', '.join(TARGET_DATES)}")
    print(f"{'='*62}")

    for ride_date in TARGET_DATES:
        print(f"\n  [{ride_date}]", end="  ")
        try:
            avail, sold = check_date(session, ride_date)
        except Exception as e:
            print(f"ERROR: {e}")
            continue

        if avail:
            any_avail = True
            print(f"✓ {len(avail)} train(s) available:")
            for t in avail:
                print(f"    車次 {t['no']:>5}  {t['type']:<4}  "
                      f"{t['dep']} → {t['arr']}  "
                      f"${t['price']}")
            
            trains_summary = "、".join(f"車次{t['no']} {t['dep']}出發" for t in avail)
            win_notify(
                f"台鐵有票！{ride_date}",
                f"{start_name}→{end_name} {ride_date}｜{trains_summary}"
            )
        elif sold:
            print(f"✗ All {len(sold)} train(s) sold out")
        else:
            print("✗ No trains / no seats found")

    print()
    if any_avail:
        print("  *** TICKETS AVAILABLE — book now! ***")
    else:
        print("  No availability found on any target date.")
    return any_avail

def run_loop(interval_seconds=60):
    print(f"Continuous check every {interval_seconds}s — Ctrl+C to stop\n")
    while True:
        run_once()
        try:
            time.sleep(interval_seconds)
        except KeyboardInterrupt:
            print("\nStopped.")
            sys.exit(0)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="台鐵訂票可用性查詢")
    parser.add_argument("--qty", type=int, default=1, metavar="N", help="查詢座位數 (default: 1)")
    parser.add_argument("--dates", nargs="+", metavar="YYYY/MM/DD", help="指定查詢日期 (default: 腳本內預設)")
    parser.add_argument("--loop", action="store_true", help="持續檢查直到 Ctrl+C")
    parser.add_argument("--interval", type=int, default=60, metavar="SECS", help="檢查間隔 (default: 60)")
    args = parser.parse_args()

    NORMAL_QTY = str(args.qty)
    if args.dates:
        TARGET_DATES = args.dates

    if args.loop:
        run_loop(args.interval)
    else:
        run_once()