#!/usr/bin/env python3
"""
อ่าน Google Sheet worksheet "Sky Money" — แสดง header และตัวอย่างข้อมูล (ไม่เขียน)
ใช้ discuss ว่าจะใส่อะไรได้บ้าง
"""
import os
import json
import base64

import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv

load_dotenv()

credentials_base64 = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
google_sheet_id = os.getenv("GOOGLE_SHEET_ID")
if not credentials_base64 or not google_sheet_id:
    print("ต้องตั้ง GOOGLE_APPLICATION_CREDENTIALS และ GOOGLE_SHEET_ID ใน .env")
    exit(1)

try:
    creds_dict = json.loads(base64.b64decode(credentials_base64).decode("utf-8"))
except Exception as e:
    print("Error decode credentials:", e)
    exit(1)

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

# หา worksheet "Sky Money" (ลองหลายแบบ)
TARGET_NAMES = ["Sky Money", "Sky money", "SkyMoney", "sky money"]

def main():
    try:
        spreadsheet = client.open_by_key(google_sheet_id)
    except Exception as e:
        print("เปิด spreadsheet ไม่ได้:", e)
        return
    # แสดงรายชื่อทุก worksheet
    worksheets = spreadsheet.worksheets()
    print("Worksheets ในไฟล์นี้:", [ws.title for ws in worksheets])
    sheet = None
    for name in TARGET_NAMES:
        try:
            sheet = spreadsheet.worksheet(name)
            print(f"\nใช้ worksheet: \"{sheet.title}\"")
            break
        except gspread.exceptions.WorksheetNotFound:
            continue
    if not sheet:
        print("\nไม่พบ worksheet 'Sky Money' — ชื่ออาจต่างกัน ลองเช็คจาก list ด้านบน")
        return
    # อ่านแถว 1 = header
    row1 = sheet.row_values(1)
    print("\n--- Header (แถว 1) ---")
    for i, cell in enumerate(row1):
        col = chr(65 + i) if i < 26 else f"A{chr(65 + i % 26)}"
        print(f"  {col}: {cell!r}")
    print(f"\nจำนวนคอลัมน์ที่มี header: {len(row1)}")
    # อ่านอีก 2–3 แถวเป็นตัวอย่าง (ถ้ามี)
    try:
        all_rows = sheet.get_all_values()
        if len(all_rows) > 1:
            print("\n--- ตัวอย่างข้อมูล (แถว 2–4) ---")
            for r in range(1, min(5, len(all_rows))):
                print(f"  แถว {r+1}: {all_rows[r][:len(row1)]}")
    except Exception as e:
        print("อ่านแถวข้อมูล:", e)
    print("\n--- จบ ---")

if __name__ == "__main__":
    main()
