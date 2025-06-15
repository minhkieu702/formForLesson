from flask import Flask, render_template_string
import yagmail
import time
import threading
from google.oauth2 import service_account
from googleapiclient.discovery import build

# === CONFIG ===
SPREADSHEET_ID = '1LRDbzejU7X6BtwOUN8c3gMbsNqCqpdeBBzEDmM1TFwI'
RANGE_NAME = "'Data'!A1:Z"
SENDER_EMAIL = 'minhkieu702@gmail.com'
EMAIL_SUBJECT = 'Cảm ơn bạn đã điền form'
EMAIL_BODY = 'Chúng tôi đã nhận được thông tin của bạn. Xin cảm ơn!'
CHECK_INTERVAL = 10  # seconds

# === SETUP GOOGLE SHEETS API ===
SERVICE_ACCOUNT_FILE = 'credentials.json'
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)
service = build('sheets', 'v4', credentials=credentials)

# === FLASK APP ===
app = Flask(__name__)

FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLScPONXC-bBvu14F4-2lT-0Yh71g-80XDGCPONa-3Vl9xyoGbQ/viewform?embedded=true"
HTML_TEMPLATE = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Google Form Embed</title>
    <style>
        body {{
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            margin: 0;
            font-family: Arial, sans-serif;
            background-color: #f5f5f5;
        }}
        h2 {{
            margin-bottom: 20px;
        }}
        iframe {{
            border: none;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            border-radius: 10px;
        }}
    </style>
</head>
<body>
    <h2>Vui lòng điền vào form bên dưới:</h2>
    <iframe src="{FORM_URL}" width="640" height="800" allowfullscreen></iframe>
</body>
</html>
"""


@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

# === BACKGROUND THREAD TO POLL FOR NEW ENTRIES ===
def poll_google_sheet():
    print("🟢 Bắt đầu kiểm tra form liên tục...")
    last_row_count = 0
    headers = []

    while True:
        try:
            sheet = service.spreadsheets()
            result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME).execute()
            rows = result.get('values', [])

            if not rows or len(rows) <= 1:
                time.sleep(CHECK_INTERVAL)
                continue

            if not headers:
                headers = rows[0]  # Lấy dòng tiêu đề (A1)

            if len(rows) > last_row_count + 1:
                new_rows = rows[last_row_count + 1:]  # Bỏ qua dòng tiêu đề
                for i, row in enumerate(new_rows):
                    try:
                        actual_row_index = last_row_count + i + 2  # +2 vì header (A1) và index bắt đầu từ 0

                        # Bỏ qua nếu chưa có đủ cột dữ liệu
                        if len(row) < 6:
                            print(f"⚠️ Dòng {actual_row_index} không đủ dữ liệu.")
                            continue

                        # Nếu đã có 'Đã gửi' trong cột M (index 12), bỏ qua
                        if len(row) >= 13 and row[12].strip().lower() == 'đã gửi':
                            continue

                        timestamp = row[0]  # Cột A: Dấu thời gian
                        email = row[11]      # Cột L: Contact email...

                        print(f"📬 Gửi email tới {email} (lúc {timestamp})")

                        yag = yagmail.SMTP(SENDER_EMAIL, 'avez ezbd ujsn kayu')  # App password
                        yag.send(
                            to=email,
                            subject=EMAIL_SUBJECT,
                            contents=f"{EMAIL_BODY}\n\n⏰ Thời gian gửi: {timestamp}"
                        )

                        # Đánh dấu vào cột M là 'Đã gửi'
                        service.spreadsheets().values().update(
                            spreadsheetId=SPREADSHEET_ID,
                            range=f"Data!M{actual_row_index}",
                            valueInputOption='RAW',
                            body={'values': [['Đã gửi']]}
                        ).execute()

                    except Exception as inner:
                        print(f"❌ Lỗi xử lý dòng mới tại dòng {actual_row_index}: {inner}")

                last_row_count = len(rows) - 1  # Cập nhật số dòng đã xử lý

        except Exception as e:
            print(f"❌ Lỗi khi truy cập Google Sheet: {e}")

        time.sleep(CHECK_INTERVAL)

# === START BACKGROUND THREAD ===
threading.Thread(target=poll_google_sheet, daemon=True).start()

if __name__ == '__main__':
    app.run(debug=True)
