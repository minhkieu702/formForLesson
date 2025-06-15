import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import lightgbm as lgb
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
import joblib

print("Bắt đầu quá trình huấn luyện model...")

# --- KẾT NỐI VỚI GOOGLE SHEETS ---
try:
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']

    # TỰ ĐỘNG TÌM ĐƯỜNG DẪN ĐẾN FILE CREDENTIALS
    # Lấy đường dẫn tuyệt đối đến thư mục chứa script đang chạy (AImodel)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Tạo đường dẫn đầy đủ và chính xác đến file credentials.json
    credentials_path = os.path.join(script_dir, 'credentials.json')

    print(f"Đang tìm file credentials tại đường dẫn: {credentials_path}")

    creds = ServiceAccountCredentials.from_json_keyfile_name(credentials_path, scope)
    client = gspread.authorize(creds)

    # THAY TÊN FILE GOOGLE SHEETS CỦA BẠN VÀO ĐÂY
    SHEET_NAME = "INS influencer_posts"
    spreadsheet = client.open(SHEET_NAME)
    print(f"Đã kết nối thành công tới Google Sheet: '{SHEET_NAME}'")

except FileNotFoundError:
    print(f"LỖI KẾT NỐI: Không tìm thấy file 'credentials.json'.")
    print("Vui lòng đảm bảo file 'credentials.json' nằm cùng thư mục với file 'train_model.py'.")
    exit()
except Exception as e:
    print(f"LỖI KẾT NỐI: {e}")
    exit()

# --- TẢI DỮ LIỆU TỪ SHEET 'influencer_posts' ---
try:
    sheet = spreadsheet.worksheet('influencer_posts')
    records = sheet.get_all_records()
    df_posts = pd.DataFrame(records)
    print(f"Đã tải thành công {len(df_posts)} dòng từ sheet 'influencer_posts'.")
except gspread.exceptions.WorksheetNotFound:
    print("LỖI: Không tìm thấy sheet 'influencer_posts'. Vui lòng kiểm tra lại tên sheet.")
    exit()

# --- XỬ LÝ DỮ LIỆU ---
# Chuyển đổi các cột số
numeric_cols = ['Likes', 'Comments', 'Shares', 'Followers', 'Post Reach']
for col in numeric_cols:
    df_posts[col] = pd.to_numeric(df_posts[col], errors='coerce')

# Chuyển đổi cột ngày tháng
df_posts['Post Date'] = pd.to_datetime(df_posts['Post Date'], errors='coerce')
df_posts.dropna(subset=numeric_cols + ['Post Date'], inplace=True)
df_posts['Hashtags'] = df_posts['Hashtags'].astype(str) # Đảm bảo Hashtags là chuỗi

# --- HUẤN LUYỆN MODEL 1: DỰ ĐOÁN HIỆU SUẤT BÀI ĐĂNG ---
print("\n--- Huấn luyện Model 1: Dự đoán Post Reach ---")

# Feature Engineering
df_posts['day_of_week'] = df_posts['Post Date'].dt.dayofweek
df_posts['hour_of_day'] = df_posts['Post Date'].dt.hour

features = ['Influencer ID', 'Content Type', 'Followers', 'day_of_week', 'hour_of_day', 'Hashtags']
target = 'Post Reach'

X = df_posts[features]
y = df_posts[target]

# Pipeline xử lý
preprocessor = ColumnTransformer(
    transformers=[
        ('cat', OneHotEncoder(handle_unknown='ignore'), ['Influencer ID', 'Content Type']),
        ('text', TfidfVectorizer(min_df=1), 'Hashtags')
    ],
    remainder='passthrough'
)

model_pipeline = Pipeline(steps=[
    ('preprocessor', preprocessor),
    ('regressor', lgb.LGBMRegressor(random_state=42, verbosity=-1))
])

# Huấn luyện model trên toàn bộ dữ liệu hiện có
model_pipeline.fit(X, y)
joblib.dump(model_pipeline, 'post_performance_predictor.joblib')
print("✅ Model 1 đã được huấn luyện và lưu vào 'post_performance_predictor.joblib'")
print("\n🎉 Hoàn tất quá trình huấn luyện!")