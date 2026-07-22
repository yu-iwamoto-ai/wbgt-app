import streamlit as st
import pandas as pd
import datetime
import requests

# --- ページ設定 ---
st.set_page_config(page_title="環境観測システム", layout="wide")

# --- セッション状態（データ保存用）の初期化 ---
if "wbgt_records" not in st.session_state:
    st.session_state.wbgt_records = []

if "sky_photo_records" not in st.session_state:
    st.session_state.sky_photo_records = []

# --- サイドバー：システム設定 ---
st.sidebar.title("⚙️ システム設定")
selected_pref = st.sidebar.selectbox(
    "学校の所在地地域",
    ["兵庫県", "東京都", "大阪府", "愛知県", "福岡県", "北海道", "沖縄県"],
    index=0
)

# --- アラート自動取得機能（bs4不使用・HTML直接判定） ---
def check_heat_alert(pref_name):
    """環境省のアラートページから直接判定"""
    clean_pref = pref_name.replace("県", "").replace("府", "").replace("都", "").replace("道", "")
    url = "https://www.wbgt.env.go.jp/sp/alert.php"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    try:
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            res.encoding = 'utf-8'
            html = res.text
            if clean_pref in html or pref_name in html:
                return True
    except Exception:
        pass
    return False

alert_active = check_heat_alert(selected_pref)

# サイドバーのアラート状態表示
with st.sidebar.expander("📡 アラート自動取得の接続状態", expanded=True):
    if alert_active:
        st.warning(f"判定: ⚠️ 発令中\n\n通信状況: 【発令中】「{selected_pref}」のアラート発表を検出しました")
    else:
        st.success(f"判定: 🟢 発表なし/平常\n\n通信状況: 現在「{selected_pref}」にアラート発令なし")
    
    if st.button("最新データに再更新"):
        st.rerun()

# --- メインヘッダー ---
st.title("☀️ 環境観測システム")

if alert_active:
    st.error(f"🚨 **【熱中症警戒アラート発表中】（{selected_pref}）**\n\n熱中症リスクが極めて高くなる見込みです。屋外活動は原則中止・延期または適切な対策を実施してください。")

# --- タブ構造 ---
tab1, tab2, tab3 = st.tabs(["🌡️ WBGT・測定登録", "📷 空の写真登録", "📊 観測データ一覧"])

# ---------------------------------------------------------
# タブ 1: WBGT・測定登録（風の状況を含む）
# ---------------------------------------------------------
with tab1:
    st.subheader("WBGTおよび気象データの登録")
    
    with st.form("wbgt_form"):
        col1, col2 = st.columns(2)
        with col1:
            record_date = st.date_input("測定日付", datetime.date.today())
            record_time = st.time_input("測定時刻", datetime.datetime.now().time())
            location = st.text_input("測定地点", value="グラウンド")
            wbgt = st.number_input("WBGT (℃)", min_value=0.0, max_value=50.0, value=28.0, step=0.1)
        
        with col2:
            temp = st.number_input("気温 (℃)", min_value=-10.0, max_value=60.0, value=31.0, step=0.1)
            humidity = st.number_input("湿度 (%)", min_value=0, max_value=100, value=65)
            # 風の状況をこちらに配置
            wind_status = st.selectbox("風の状況", ["なし 🍃", "弱風 🌬️", "強風 💨"])
            memo = st.text_input("備考・メモ", value="")
            
        submit_wbgt = st.form_submit_button("データを保存")
        
        if submit_wbgt:
            st.session_state.wbgt_records.append({
                "日付": record_date.strftime("%Y-%m-%d"),
                "時刻": record_time.strftime("%H:%M"),
                "地点": location,
                "WBGT(℃)": wbgt,
                "気温(℃)": temp,
                "湿度(%)": humidity,
                "風の状況": wind_status,
                "備考": memo
            })
            st.success("WBGTデータを登録しました！")

# ---------------------------------------------------------
# タブ 2: 空の写真登録（地点不要・日付と時刻のみ）
# ---------------------------------------------------------
with tab2:
    st.subheader("空の写真登録")
    
    with st.form("sky_photo_form"):
        col1, col2 = st.columns(2)
        with col1:
            photo_date = st.date_input("撮影日付", datetime.date.today())
            photo_time = st.time_input("撮影時刻", datetime.datetime.now().time())
        
        uploaded_file = st.file_uploader("空の画像をアップロード", type=["jpg", "jpeg", "png"])
        photo_memo = st.text_input("写真に関するメモ（任意）", value="")
        
        submit_photo = st.form_submit_button("写真を保存")
        
        if submit_photo:
            if uploaded_file is not None:
                st.session_state.sky_photo_records.append({
                    "日付": photo_date.strftime("%Y-%m-%d"),
                    "時刻": photo_time.strftime("%H:%M"),
                    "画像データ": uploaded_file,
                    "メモ": photo_memo
                })
                st.success("空の写真を登録しました！")
            else:
                st.warning("画像ファイルを選択してください。")

# ---------------------------------------------------------
# タブ 3: 観測データ一覧
# ---------------------------------------------------------
with tab3:
    st.subheader("📋 記録データ一覧")
    
    sub_tab1, sub_tab2 = st.tabs(["WBGT観測履歴", "📷 空の写真一覧"])
    
    with sub_tab1:
        if st.session_state.wbgt_records:
            df_wbgt = pd.DataFrame(st.session_state.wbgt_records)
            st.dataframe(df_wbgt, use_container_width=True)
        else:
            st.info("登録されたWBGTデータはまだありません。")
            
    with sub_tab2:
        if st.session_state.sky_photo_records:
            photo_table_data = []
            for item in st.session_state.sky_photo_records:
                photo_table_data.append({
                    "日付": item["日付"],
                    "時刻": item["時刻"],
                    "メモ": item["メモ"]
                })
            
            st.markdown("##### 📝 写真の記録一覧")
            st.dataframe(pd.DataFrame(photo_table_data), use_container_width=True)
            
            st.divider()
            st.markdown("##### 🖼️ ギャラリー表示")
            
            cols = st.columns(3)
            for idx, item in enumerate(st.session_state.sky_photo_records):
                with cols[idx % 3]:
                    st.image(item["画像データ"], caption=f"{item['日付']} {item['時刻']} - {item['メモ']}", use_container_width=True)
        else:
            st.info("登録された空の写真はまだありません。")
