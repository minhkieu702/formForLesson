import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
from sklearn.preprocessing import minmax_scale

print("Bắt đầu hệ thống gợi ý Influmate...")


# --- HÀM TIỆN ÍCH ---
def load_data(script_dir):
    """Tải hồ sơ influencer từ file CSV và yêu cầu từ Google Sheets."""
    try:
        # Tải hồ sơ đã được xử lý sẵn
        profiles_path = os.path.join(script_dir, 'influencer_profiles.csv')
        if not os.path.exists(profiles_path):
            print(f"❌ Lỗi: Không tìm thấy file 'influencer_profiles.csv'.")
            print("Vui lòng chạy file 'profiler.py' trước để tạo hồ sơ.")
            return None, None
        df_profiles = pd.read_csv(profiles_path)
        print(f"✅ Đã tải {len(df_profiles)} hồ sơ influencer từ file cục bộ.")

        # Kết nối và tải yêu cầu mới nhất từ doanh nghiệp
        credentials_path = os.path.join(script_dir, 'credentials.json')
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name(credentials_path, scope)
        client = gspread.authorize(creds)

        spreadsheet_forms = client.open("InfluMate")
        sheet_requests = spreadsheet_forms.worksheet("Data")
        df_requests = pd.DataFrame(sheet_requests.get_all_records())
        print(f"✅ Đã tải {len(df_requests)} yêu cầu từ doanh nghiệp.")

        return df_profiles, df_requests

    except Exception as e:
        print(f"❌ Đã xảy ra lỗi khi tải dữ liệu: {e}")
        return None, None


def get_recommendations(campaign, influencer_profiles):
    """Tính điểm và xếp hạng influencer cho một chiến dịch cụ thể."""
    print(f"\n[Bắt đầu] Tìm kiếm cho chiến dịch: '{campaign.get('campaign_goal', 'Không rõ')}'")

    scores = []
    profiles_scaled = influencer_profiles.copy()
    metrics_to_scale = ['avg_engagement_rate', 'avg_share_rate', 'avg_comment_rate', 'avg_reach_rate']
    profiles_scaled[metrics_to_scale] = minmax_scale(profiles_scaled[metrics_to_scale])

    campaign_goal = campaign.get('campaign_goal', '').lower()

    for _, influencer in profiles_scaled.iterrows():
        score = 0
        # Thiết lập trọng số dựa trên mục tiêu chiến dịch
        if 'brand awareness' in campaign_goal:
            score += influencer['avg_reach_rate'] * 0.6 + influencer['avg_share_rate'] * 0.2 + (
                0.2 if influencer['kol_tier'] in ['Macro', 'Mega'] else 0)
        elif 'engagement' in campaign_goal:
            score += influencer['avg_engagement_rate'] * 0.5 + influencer['avg_comment_rate'] * 0.4 + (
                0.1 if influencer['kol_tier'] in ['Nano', 'Micro'] else 0)
        elif 'sales' in campaign_goal or 'attract new users' in campaign_goal:
            score += influencer['avg_engagement_rate'] * 0.6 + influencer['avg_comment_rate'] * 0.2 + (
                0.2 if influencer['kol_tier'] in ['Nano', 'Micro'] else 0)
        elif 'launch a new product' in campaign_goal:
            score += influencer['avg_reach_rate'] * 0.4 + influencer['avg_engagement_rate'] * 0.4 + (
                0.2 if influencer['kol_tier'] in ['Micro', 'Macro'] else 0)
        else:
            score += influencer['avg_engagement_rate'] * 0.5 + influencer['avg_reach_rate'] * 0.5
        scores.append(score)

    influencer_profiles['match_score'] = scores
    return influencer_profiles.sort_values(by='match_score', ascending=False)


# --- LUỒNG THỰC THI CHÍNH ---
if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    influencer_profiles, df_requests = load_data(script_dir)

    if influencer_profiles is not None and df_requests is not None:
        if not df_requests.empty:
            latest_request = df_requests.iloc[-1].to_dict()
            final_ranked_list = get_recommendations(latest_request, influencer_profiles)

            print("\n" + "=" * 80)
            print("🏆 KẾT QUẢ GỢI Ý INFLUENCER PHÙ HỢP NHẤT (ĐÃ XẾP HẠNG) 🏆")
            print("=" * 80)
            display_cols = [
                'Influencer ID',
                'match_score',
                'kol_tier',
                'followers',
                'avg_engagement_rate',
                'avg_reach_rate'
            ]
            final_ranked_list_display = final_ranked_list[display_cols].copy()
            final_ranked_list_display['match_score'] = final_ranked_list_display['match_score'].round(4)
            final_ranked_list_display['avg_engagement_rate'] = (final_ranked_list_display[
                                                                    'avg_engagement_rate'] * 100).round(2).astype(
                str) + '%'
            final_ranked_list_display['avg_reach_rate'] = (final_ranked_list_display['avg_reach_rate'] * 100).round(
                2).astype(str) + '%'
            print(final_ranked_list_display.to_string(index=False))
            print("=" * 80)
        else:
            print("⚠️ Không có yêu cầu nào từ doanh nghiệp trong sheet 'Data'.")