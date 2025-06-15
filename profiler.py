import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os

print("Bắt đầu quá trình tạo hồ sơ năng lực Influencer...")


# --- HÀM TIỆN ÍCH ---
def get_kol_tier(followers):
    """Phân loại cấp bậc Influencer dựa trên lượng followers."""
    try:
        followers = int(followers)
        if followers < 10000: return 'Nano'
        if followers < 100000: return 'Micro'
        if followers < 1000000: return 'Macro'
        return 'Mega'
    except (ValueError, TypeError):
        return 'Unknown'


def create_influencer_profiles(df_posts):
    """
    Phân tích và xây dựng hồ sơ năng lực cho từng influencer.
    """
    print("-> Đang tính toán các chỉ số...")

    # Chuyển đổi kiểu dữ liệu, xử lý lỗi nếu có ký tự không phải số
    numeric_cols = ['Likes', 'Comments', 'Shares', 'Followers', 'Post Reach']
    for col in numeric_cols:
        df_posts[col] = pd.to_numeric(df_posts[col].astype(str).str.replace(',', ''), errors='coerce')
    df_posts.dropna(subset=numeric_cols, inplace=True)

    # Tính toán các chỉ số trên mỗi bài đăng
    df_posts['Interactions'] = df_posts['Likes'] + df_posts['Comments'] + df_posts['Shares']

    # Thêm điều kiện tránh chia cho 0
    df_posts = df_posts[df_posts['Followers'] > 0]

    df_posts['Engagement Rate'] = df_posts['Interactions'] / df_posts['Followers']
    df_posts['Share Rate'] = df_posts['Shares'] / df_posts['Followers']
    df_posts['Comment Rate'] = df_posts['Comments'] / df_posts['Followers']
    df_posts['Reach Rate'] = df_posts['Post Reach'] / df_posts['Followers']

    # Tổng hợp dữ liệu cho mỗi influencer
    influencer_profiles = df_posts.groupby('Influencer ID').agg(
        avg_interactions=('Interactions', 'mean'),
        avg_engagement_rate=('Engagement Rate', 'mean'),
        avg_share_rate=('Share Rate', 'mean'),
        avg_comment_rate=('Comment Rate', 'mean'),
        avg_reach_rate=('Reach Rate', 'mean'),
        followers=('Followers', 'last')  # Lấy lượng follower mới nhất
    ).reset_index()

    # Phân loại cấp bậc
    influencer_profiles['kol_tier'] = influencer_profiles['followers'].apply(get_kol_tier)

    print(f"-> Đã tạo hồ sơ cho {len(influencer_profiles)} influencers.")
    return influencer_profiles


# --- LUỒNG THỰC THI CHÍNH ---
if __name__ == "__main__":
    try:
        # Kết nối và tải dữ liệu
        script_dir = os.path.dirname(os.path.abspath(__file__))
        credentials_path = os.path.join(script_dir, 'credentials.json')
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name(credentials_path, scope)
        client = gspread.authorize(creds)

        spreadsheet_posts = client.open("INS influencer_posts")
        sheet_posts = spreadsheet_posts.worksheet("posts")  # Tên sheet đã sửa
        df_posts = pd.DataFrame(sheet_posts.get_all_records())
        print(f"✅ Đã tải thành công {len(df_posts)} dòng dữ liệu bài đăng.")

        # Tạo hồ sơ
        profiles = create_influencer_profiles(df_posts)

        # Lưu hồ sơ ra file CSV để sử dụng sau này
        output_path = os.path.join(script_dir, 'influencer_profiles.csv')
        profiles.to_csv(output_path, index=False, encoding='utf-8-sig')
        print(f"✅ Hồ sơ đã được lưu vào file: {output_path}")
        print("\n🎉 Hoàn tất quá trình tạo hồ sơ!")

    except Exception as e:
        print(f"❌ Đã xảy ra lỗi: {e}")