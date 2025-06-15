import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
from sklearn.preprocessing import minmax_scale
import plotly.graph_objects as go
from workflow import send_dashboard_link

# Cấu hình trang Dashboard
st.set_page_config(layout="wide", page_title="Influmate AI Recommender")


# --- BỘ NHỚ CACHE ---
# @st.cache_data(ttl=600)  # Tắt cache tạm thời
def load_data(script_dir):
    try:
        profiles_path = os.path.join(script_dir, 'influencer_profiles.csv')
        df_profiles = pd.read_csv(profiles_path)

        credentials_path = os.path.join(script_dir, 'credentials.json')
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name(credentials_path, scope)
        client = gspread.authorize(creds)

        spreadsheet_forms = client.open("InfluMate")
        sheet_requests = spreadsheet_forms.worksheet("Data")
        df_requests = pd.DataFrame(sheet_requests.get_all_records())

        return df_profiles, df_requests
    except Exception as e:
        st.error(f"Lỗi tải dữ liệu: {e}")
        return None, None


# --- CÁC HÀM LOGIC (Giữ nguyên từ recommender.py) ---
def get_recommendations(campaign, influencer_profiles):
    # (Copy toàn bộ nội dung hàm get_recommendations từ file recommender.py vào đây)
    scores = []
    profiles_scaled = influencer_profiles.copy()
    metrics_to_scale = ['avg_engagement_rate', 'avg_share_rate', 'avg_comment_rate', 'avg_reach_rate']
    profiles_scaled[metrics_to_scale] = minmax_scale(profiles_scaled[metrics_to_scale])
    campaign_goal = campaign.get('campaign_goal', '').lower()
    for _, influencer in profiles_scaled.iterrows():
        score = 0
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


def create_bar_chart(df, username):
    """Tạo biểu đồ cột cho một influencer cụ thể"""
    influencer_profiles = df[df['username'] == username].iloc[0]
    
    fig = go.Figure(data=[
        go.Bar(name='Followers', x=['Followers'], y=[influencer_profiles['followers']]),
        go.Bar(name='Likes', x=['Likes'], y=[influencer_profiles['likescount']]),
        go.Bar(name='Comments', x=['Comments'], y=[influencer_profiles['commentscount']])
    ])
    
    fig.update_layout(
        title=f'Thống kê của {username}',
        barmode='group',
        showlegend=True
    )
    
    return fig


# --- XÂY DỰNG GIAO DIỆN DASHBOARD ---

st.title("🚀 Influmate - AI Recommender Dashboard")

# Tạo tabs cho các phần khác nhau của dashboard
tab1, tab2 = st.tabs(["📊 Thống kê Influencer", "📝 Đăng ký Chiến dịch"])

# Thêm nút đăng xuất vào sidebar
with st.sidebar:
    st.markdown("---")  # Thêm đường kẻ phân cách
    if st.button("🚪 Đăng xuất", type="primary", use_container_width=True):
        st.session_state.clear()  # Xóa tất cả session state
        st.rerun()  # Tải lại trang

with tab1:
    st.write("Thống kê và phân tích dữ liệu Influencer")
    
    # Tải dữ liệu
    script_dir = os.path.dirname(os.path.abspath(__file__))
    influencer_profiles, df_requests = load_data(script_dir)

    if influencer_profiles is not None and df_requests is not None:
        # Hiển thị danh sách influencer để chọn
        selected_username = st.selectbox(
            "Chọn Influencer để xem thống kê:",
            options=influencer_profiles['username'].unique()
        )
        
        # Tạo và hiển thị biểu đồ
        if selected_username:
            fig = create_bar_chart(influencer_profiles, selected_username)
            st.plotly_chart(fig, use_container_width=True)
            
            # Hiển thị thông tin chi tiết
            st.subheader("Thông tin chi tiết")
            influencer_info = influencer_profiles[influencer_profiles['username'] == selected_username].iloc[0]
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Followers", f"{influencer_info['followers']:,}")
            with col2:
                st.metric("Likes", f"{influencer_info['likescount']:,}")
            with col3:
                st.metric("Comments", f"{influencer_info['commentscount']:,}")
    else:
        st.error("Không thể tải dữ liệu, vui lòng kiểm tra lại kết nối và file.")

with tab2:
    st.header("📝 Đăng ký Chiến dịch Mới")
    st.write("Vui lòng điền thông tin chiến dịch của bạn vào form bên dưới:")
    
    # Nhúng Google Form
    google_form_url = "https://docs.google.com/forms/d/e/1FAIpQLSdcwgPmynO6D2eailGclDiy6_JnHsPWb4XrYOkHzeGWwBJ4qA/viewform?embedded=true"
    st.components.v1.iframe(google_form_url, height=800, scrolling=True)