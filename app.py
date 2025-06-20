from flask import Flask, render_template_string
import time
import threading
import pandas as pd
import matplotlib.pyplot as plt
from fpdf import FPDF
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# === CONFIG ===
SPREADSHEET_ID = '19gc4qsNR45ek_P-h4XBGeHyPvTR8tXPMllv6vu6aKr8'  # form sheet
INFLUENCER_SPREADSHEET_ID = '18Pw59giiDPGEF4Z32PxhXljhGsGrhenz4lRoqQBHxxM'
RANGE_NAME = "'Data'!A1:Z"
CHECK_INTERVAL = 10
SERVICE_ACCOUNT_FILE = 'credentials.json'
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
DASHBOARD_FOLDER_ID = '1mc1YjttlTCaG4XwpIuVSnImdWBEh1-YL'  # Drive folder

# === GOOGLE API SETUP ===
credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
sheets_service = build('sheets', 'v4', credentials=credentials)
drive_service = build('drive', 'v3', credentials=credentials)

# === FLASK APP ===
app = Flask(__name__)
FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSdcwgPmynO6D2eailGclDiy6_JnHsPWb4XrYOkHzeGWwBJ4qA/viewform?embedded=true"
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
        h2 {{ margin-bottom: 20px; }}
        iframe {{ border: none; box-shadow: 0 4px 12px rgba(0,0,0,0.15); border-radius: 10px; }}
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


# === UTILITIES ===
def generate_dashboard_pdf(row_data, output_path='dashboard.pdf'):
        #  Parse dữ liệu chiến dịch từ 1 dòng của Google Sheet (dữ liệu form gửi lên)
    headers = ['Timestamp', 'Business', 'Industry', 'Goal', 'KOL Type', 'Country', '', '', '', '', '', 'Email']
    data = dict(zip(headers, row_data[:len(headers)]))
    country = str(data.get("Country", "")).strip().lower()
    kol_type = str(data.get("KOL Type", "")).strip().lower().split()[0]

    # 1. Đọc dữ liệu từ Google Sheet
    result = sheets_service.spreadsheets().values().get(
        spreadsheetId=INFLUENCER_SPREADSHEET_ID,
        range="'Data'!A1:Z"
    ).execute()
    rows = result.get('values', [])
    if not rows or len(rows) < 2:
        raise Exception("Không có dữ liệu influencer!")

    df_all = pd.DataFrame(rows[1:], columns=rows[0])

    # 2. Làm sạch & xử lý định dạng dữ liệu
    df = df_all.copy()
    df['raw_followers'] = pd.to_numeric(df['raw_followers'], errors='coerce').fillna(0).astype(int)
    df['avgLikes'] = pd.to_numeric(df['avgLikes'], errors='coerce').fillna(0).astype(int)
    df['avgComments'] = pd.to_numeric(df['avgComments'], errors='coerce').fillna(0).astype(int)
    df['engagement'] = df['engagement'].astype(str).str.replace(',', '.').astype(float)
    df['location'] = df['location'].str.replace(r'[\[\]"]', '', regex=True).str.lower().str.strip()
    df['tier'] = df['raw_followers'].apply(lambda x:
        'Nano' if x < 10000 else
        'Micro' if x < 100000 else
        'Macro' if x < 500000 else
        'Mega'
    )

    # 3. Lọc theo tiêu chí chiến dịch
    filtered_df = df.copy()
    if country:
        filtered_df = filtered_df[filtered_df['location'] == country]
    if kol_type and kol_type != 'n/a':
        filtered_df = filtered_df[filtered_df['tier'].str.lower() == kol_type]

    if filtered_df.empty:
        print("⚠️ Không tìm thấy influencer phù hợp. Sẽ chọn top 3 nổi tiếng nhất.")
        top_df = df.sort_values(by='raw_followers', ascending=False).head(3)
    else:
        filtered_df['score'] = filtered_df['raw_followers'] * 0.6 + filtered_df['engagement'] * 0.4
        top_df = filtered_df.sort_values(by='score', ascending=False).head(3)

    # 4. Vẽ biểu đồ
    plt.figure(figsize=(6, 4))
    top_df.set_index('username')[['raw_followers', 'avgLikes', 'avgComments']].plot(
        kind='bar', color=['yellow', 'red', 'blue'])
    plt.title("Top 3 Influencers")
    plt.tight_layout()
    chart_path = 'chart.png'
    plt.savefig(chart_path)
    plt.close()

    # 5. Xuất PDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "Influencer Campaign Dashboard", ln=True)

    pdf.set_font("Arial", '', 12)
    for key in ['Business', 'Industry', 'Goal', 'KOL Type', 'Country']:
        pdf.cell(0, 8, f"{key}: {data.get(key, '')}", ln=True)

    pdf.ln(5)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, "Top Influencers:", ln=True)

    pdf.set_font("Arial", '', 11)
    for i, row in top_df.iterrows():
        pdf.cell(0, 8, f"{row['username']} - {row['tier']} | {row['raw_followers']} F | {row['avgLikes']} L | {row['avgComments']} C", ln=True)

    pdf.ln(5)
    pdf.image(chart_path, x=10, w=pdf.w - 20)
    pdf.output(output_path)
    return output_path


def upload_to_drive(filepath):
    file_metadata = {
        'name': filepath,
        'parents': [DASHBOARD_FOLDER_ID]
    }
        #  Tạo file PDF trên Google Drive và chia sẻ public link
    media = MediaFileUpload(filepath, mimetype='application/pdf')
    uploaded = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    file_id = uploaded.get('id')
        #  Cấp quyền xem công khai cho file
    drive_service.permissions().create(
        fileId=file_id,
        body={'role': 'reader', 'type': 'anyone'}
    ).execute()

    return f"https://drive.google.com/file/d/{file_id}/view?usp=sharing"


# === BACKGROUND THREAD ===
def poll_google_sheet():
    print("🟢 Đang kiểm tra sheet...")
    last_row_count = 0
    headers = []

    while True:
        try:
            #  Đọc dữ liệu từ sheet form
            sheet = sheets_service.spreadsheets()
            result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME).execute()
            rows = result.get('values', [])

            if not rows or len(rows) <= 1:
                time.sleep(CHECK_INTERVAL)
                continue

            if not headers:
                headers = rows[0]

            #  Kiểm tra nếu có dòng mới chưa được xử lý
            if len(rows) > last_row_count + 1:
                new_rows = rows[last_row_count + 1:]
                for i, row in enumerate(new_rows):
                    actual_row_index = last_row_count + i + 2 # +2 vì dòng tiêu đề + index base-0
                    if len(row) < 6:
                        print(f"⚠️ Dòng {actual_row_index} không đủ dữ liệu.")
                        continue
                    if len(row) >= 13 and row[12].strip():
                        continue  # Đã xử lý trước đó

                    try:
                         # Tạo dashboard → upload Drive → lấy link
                        pdf_path = generate_dashboard_pdf(row)
                        drive_link = upload_to_drive(pdf_path)

                        # Ghi link vào cột M
                        sheet.values().update(
                            spreadsheetId=SPREADSHEET_ID,
                            range=f"Data!M{actual_row_index}",
                            valueInputOption='RAW',
                            body={'values': [[drive_link]]}
                        ).execute()

                        print(f"✅ Đã xử lý dòng {actual_row_index}, link: {drive_link}")

                    except Exception as inner:
                        print(f"❌ Lỗi xử lý dòng {actual_row_index}: {inner}")

                last_row_count = len(rows) - 1 # Cập nhật vị trí xử lý

        except Exception as e:
            print(f"❌ Lỗi khi truy cập Google Sheet: {e}")

        time.sleep(CHECK_INTERVAL)


# === RUN FLASK + THREAD ===
threading.Thread(target=poll_google_sheet, daemon=True).start()

if __name__ == '__main__':
    app.run(debug=True)
