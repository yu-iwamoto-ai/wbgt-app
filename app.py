# -*- coding: utf-8 -*-
import streamlit as st
import os
import pandas as pd
import requests
from datetime import datetime, date
from PIL import Image, ImageOps

# ページの設定
st.set_page_config(page_title="校内WBGT観測システム", page_icon="🌡️", layout="centered")

# フォルダの設定
IMAGE_DIR = "saved_images"
os.makedirs(IMAGE_DIR, exist_ok=True)

# 都道府県リスト
PREFECTURES = [
    "東京都", "神奈川県", "埼玉県", "千葉県", "大阪府", "兵庫県", "京都府", "愛知県",
    "北海道", "青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県", "茨城県",
    "栃木県", "群馬県", "新潟県", "富山県", "石川県", "福井県", "山梨県", "長野県",
    "岐阜県", "静岡県", "三重県", "滋賀県", "奈良県", "和歌山県", "鳥取県",
    "島根県", "岡山県", "広島県", "山口県", "徳島県", "香川県", "愛媛県", "高知県",
    "福岡県", "佐賀県", "長崎県", "熊本県", "大分県", "宮崎県", "鹿児島県", "沖縄県"
]

# 地点設定
LOCATIONS_WBGT = ["講堂", "柏倫館", "エントランス", "東門付近", "西館3F"]
LOCATIONS_ENV = ["校内全体（全地点共通）", "正門付近", "東門付近", "グラウンド", "南館屋上", "建学の庭付近"]

# 「エントランス」と「正門付近」の同義関係定義
LOCATION_MAPPING = {
    "エントランス": "正門付近",
    "正門付近": "エントランス"
}

# 相互参照（天候紐付け）を行う特定2地点のリスト
REFLECT_WEATHER_LOCATIONS = ["東門付近", "エントランス", "正門付近"]

WEATHERS = ["晴れ ☀️", "曇り ☁️", "雨 🌧️", "室内 🏢"]
WINDS = ["なし 🍃", "弱風 🌬️", "強風 💨"]

REQUIRED_COLUMNS = ["日時", "地点", "天候", "風", "WBGT", "気温", "湿度", "表面温度", "判定", "画像", "空画像", "表面画像"]

# データフレームのカラム補正関数
def ensure_columns(df):
    for col in REQUIRED_COLUMNS:
        if col not in df.columns:
            df[col] = "-"
    return df[REQUIRED_COLUMNS]

# メモリ空間の保持
@st.cache_resource(ttl=86400)
def get_secure_database():
    return {"df": pd.DataFrame(columns=REQUIRED_COLUMNS)}

db_container = get_secure_database()

# CSVファイルバックアップ準備
DB_FILE = "wbgt_data.csv"
if not os.path.exists(DB_FILE):
    df_init = pd.DataFrame(columns=REQUIRED_COLUMNS)
    df_init.to_csv(DB_FILE, index=False, encoding="utf-8-sig")
else:
    try:
        file_df = pd.read_csv(DB_FILE, encoding="utf-8-sig")
        file_df = ensure_columns(file_df)
        if db_container["df"].empty and not file_df.empty:
            db_container["df"] = file_df
    except Exception:
        pass

db_container["df"] = ensure_columns(db_container["df"])

# 熱中症警戒アラートの自動取得関数（強固版）
@st.cache_data(ttl=1800) # 30分キャッシュ
def check_heat_alert_status(pref_name):
    clean_pref = pref_name.replace("県", "").replace("府", "").replace("都", "")
    
    # 環境省 / 気象庁アラートデータ取得（マルチフォールバック）
    urls = [
        "https://www.wbgt.env.go.jp/sp/data/xml/alert_info.xml",
        "https://www.wbgt.env.go.jp/prev157/data/alert_info.xml"
    ]
    
    status_msg = "取得未実行"
    is_alert = False
    
    for url in urls:
        try:
            res = requests.get(url, timeout=4)
            if res.status_code == 200:
                content = res.text
                if clean_pref in content or pref_name in content:
                    is_alert = True
                    status_msg = f"【発令中】データ内に{pref_name}を確認しました"
                else:
                    status_msg = f"【正常通信】現在{pref_name}に発令データはありません"
                break
        except Exception as e:
            status_msg = f"通信エラー: {e}"
            
    return is_alert, status_msg

# 熱中症判定のルール（5段階）
def judge_wbgt(val):
    if val >= 33: return "🟣 危険（熱中症警戒アラート）", "#800080"
    elif val >= 31: return "🔴 危険", "#FF4B4B"
    elif val >= 28: return "🔶 厳重警戒", "#FFA500"
    elif val >= 25: return "💛 警戒", "#F1C40F"
    else: return "🔹 注意", "#3498DB"

# 画像保存用ヘルパー関数
def save_uploaded_image(file_obj, prefix, dt_str, loc_str):
    if file_obj is None:
        return "-"
    filename = f"{prefix}_{dt_str}_{loc_str}.jpg"
    filepath = os.path.join(IMAGE_DIR, filename)
    try:
        image = Image.open(file_obj)
        image = ImageOps.exif_transpose(image)
        image.save(filepath, "JPEG", quality=85)
    except Exception:
        with open(filepath, "wb") as f:
            f.write(file_obj.getbuffer())
    return filename

# 画像ポップアップ（モーダル）表示用関数
@st.dialog("🖼️ 写真の表示")
def show_image_modal(image_path, title="写真"):
    st.image(image_path, caption=title, use_container_width=True)

# ------------------------------------------
# サイドバー設定 ＆ アラート状態診断
# ------------------------------------------
st.sidebar.header("⚙️ システム設定")
selected_pref = st.sidebar.selectbox("学校の所在地域", PREFECTURES, index=PREFECTURES.index("兵庫県") if "兵庫県" in PREFECTURES else 0)

# 自動取得処理実行
auto_alert, alert_debug_msg = check_heat_alert_status(selected_pref)

# サイドバーに自動取得の診断結果を表示（デバッグ・安心用）
with st.sidebar.expander("📡 アラート自動取得の接続状態", expanded=False):
    st.caption(f"判定結果: **{'⚠️ 発令あり' if auto_alert else '🟢 発令なし/平常'}**")
    st.caption(f"詳細情報: {alert_debug_msg}")
    if st.button("最新状態に更新（再取得）"):
        st.cache_data.clear()
        st.rerun()

# 手動強制表示スイッチ（テスト・緊急時用）
manual_alert = st.sidebar.checkbox("熱中症警戒アラートをテスト表示（強制表示）", value=False)

is_alert_active = auto_alert or manual_alert

# ------------------------------------------
# メイン画面ヘッダー ＆ アラート表示
# ------------------------------------------
st.title("🌡️ 校内WBGT・環境観測システム")

# 熱中症警戒アラートが発令されている場合、最上部に表示
if is_alert_active:
    st.markdown(
        f"""
        <div style="background-color: #FF2E2E; color: white; padding: 14px; border-radius: 8px; text-align: center; font-weight: bold; font-size: 1.15rem; margin-bottom: 15px; box-shadow: 0px 4px 10px rgba(255, 0, 0, 0.3); border: 2px solid #B30000;">
            ⚠️ 【熱中症警戒アラート発表中】 ({selected_pref})<br>
            <span style="font-size: 0.95rem; font-weight: normal;">本日・明日は暑さ指数（WBGT）が著しく高くなる見込みです。屋外活動は原則中止・厳重警戒してください。</span>
        </div>
        """,
        unsafe_allow_html=True
    )

st.caption("WBGT数値データ ＋ 天候・地面表面温度・写真保存（機器・空・表面温度）")

tab1, tab2, tab3 = st.tabs(["📸 新規登録", "📋 地点別最新一覧", "📊 全履歴（CSV）"])

# ==========================================
# タブ1: 新規登録
# ==========================================
with tab1:
    st.header("新規データの登録")
    
    sub_tab_a, sub_tab_b = st.tabs(["🌡️ WBGT・測定値登録", "🌤️ 天候・表面温度・写真登録"])
    
    # --- サブタブA: WBGT数値の入力 ---
    with sub_tab_a:
        st.subheader("1. WBGT・気象数値の入力")
        loc_a = st.selectbox("観測地点を選択", LOCATIONS_WBGT, key="loc_a")
        
        c_date_a, c_time_a = st.columns(2)
        with c_date_a:
            date_a = st.date_input("観測日を選択", date.today(), key="date_a")
        with c_time_a:
            now_time_str = datetime.now().strftime("%H:%M")
            time_a_str = st.text_input("観測時刻", value=now_time_str, key="time_a", help="例: 15:30")
        
        time_part_a = time_a_str.strip()
        if len(time_part_a) == 5: time_part_a += ":00"
        elif len(time_part_a) == 4 and ":" in time_part_a: time_part_a = "0" + time_part_a + ":00"
        dt_str_a = f"{date_a} {time_part_a}"
        
        st.write("---")
        wbgt_a = st.number_input("WBGT (℃)", value=25.0, step=0.1, format="%.1f", key="wbgt_a")
        ta_a = st.number_input("気温 (℃)", value=30.0, step=0.1, format="%.1f", key="ta_a")
        rh_a = st.number_input("湿度 (%)", value=60.0, step=0.1, format="%.1f", key="rh_a")
        
        uploaded_main_a = st.file_uploader("📷 測定機器の証拠写真（任意）", type=["jpg", "jpeg", "png"], key="img_a")
        
        if st.button("数値データを登録する", type="primary", key="btn_a"):
            try:
                datetime.strptime(dt_str_a, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                st.error("時刻の入力形式が正しくありません。「15:30」のように入力してください。")
                st.stop()
                
            judgment, _ = judge_wbgt(wbgt_a)
            dt_stamp = f"{date_a.strftime('%Y%m%d')}_{time_part_a.replace(':', '')}"
            img_name = save_uploaded_image(uploaded_main_a, "main", dt_stamp, loc_a)
            
            df = db_container["df"]
            match_mask = (df["日時"] == dt_str_a) & (df["地点"] == loc_a)
            
            if not df[match_mask].empty:
                idx = df[match_mask].index[-1]
                db_container["df"].loc[idx, "WBGT"] = wbgt_a
                db_container["df"].loc[idx, "気温"] = ta_a
                db_container["df"].loc[idx, "湿度"] = rh_a
                db_container["df"].loc[idx, "判定"] = judgment
                if img_name != "-": db_container["df"].loc[idx, "画像"] = img_name
                st.success(f"【更新完了】 {loc_a} ({dt_str_a}) の測定データを更新しました！")
            else:
                new_row = pd.DataFrame([[dt_str_a, loc_a, "-", "-", wbgt_a, ta_a, rh_a, "-", judgment, img_name, "-", "-"]], 
                                       columns=REQUIRED_COLUMNS)
                db_container["df"] = pd.concat([db_container["df"], new_row], ignore_index=True)
                st.success(f"【登録完了】 {loc_a} ({dt_str_a}) の測定データを保存しました！")
                
            db_container["df"].to_csv(DB_FILE, index=False, encoding="utf-8-sig")
            st.rerun()

    # --- サブタブB: 天候・表面温度の入力 ---
    with sub_tab_b:
        st.subheader("2. 天候・地面の表面温度データの入力")
        loc_b = st.selectbox("対象を選択", LOCATIONS_ENV, key="loc_b")
        
        c_date_b, c_time_b = st.columns(2)
        with c_date_b:
            date_b = st.date_input("観測日を選択", date.today(), key="date_b")
        with c_time_b:
            now_time_str = datetime.now().strftime("%H:%M")
            time_b_str = st.text_input("観測時刻", value=now_time_str, key="time_b", help="例: 15:30")
            
        time_part_b = time_b_str.strip()
        if len(time_part_b) == 5: time_part_b += ":00"
        elif len(time_part_b) == 4 and ":" in time_part_b: time_part_b = "0" + time_part_b + ":00"
        dt_str_b = f"{date_b} {time_part_b}"
        
        st.write("---")
        weather_b = st.selectbox("天候を選択", WEATHERS, key="weather_b")
        wind_b = st.selectbox("風の有無を選択", WINDS, key="wind_b")
        surface_temp_b = st.number_input("地面の表面温度 (℃)", value=30.0, step=0.1, format="%.1f", key="surface_temp_b")
        
        c_img_sky, c_img_surf = st.columns(2)
        with c_img_sky:
            uploaded_sky_b = st.file_uploader("🌤️ 空の写真（任意）", type=["jpg", "jpeg", "png"], key="sky_b")
        with c_img_surf:
            uploaded_surf_b = st.file_uploader("🌡️ 表面温度の写真（任意）", type=["jpg", "jpeg", "png"], key="surf_b")
        
        if st.button("天候・表面温度データを登録する", type="primary", key="btn_b"):
            try:
                datetime.strptime(dt_str_b, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                st.error("時刻の入力形式が正しくありません。「15:30」のように入力してください。")
                st.stop()
                
            dt_stamp = f"{date_b.strftime('%Y%m%d')}_{time_part_b.replace(':', '')}"
            sky_img_name = save_uploaded_image(uploaded_sky_b, "sky", dt_stamp, loc_b)
            surf_img_name = save_uploaded_image(uploaded_surf_b, "surf", dt_stamp, loc_b)
            
            df = db_container["df"]
            match_mask = (df["日時"] == dt_str_b) & (df["地点"] == loc_b)
            
            if not df[match_mask].empty:
                idx = df[match_mask].index[-1]
                db_container["df"].loc[idx, "天候"] = weather_b
                db_container["df"].loc[idx, "風"] = wind_b
                db_container["df"].loc[idx, "表面温度"] = surface_temp_b
                if sky_img_name != "-": db_container["df"].loc[idx, "空画像"] = sky_img_name
                if surf_img_name != "-": db_container["df"].loc[idx, "表面画像"] = surf_img_name
                st.success(f"【更新完了】 {loc_b} ({dt_str_b}) の天候情報を更新しました！")
            else:
                new_row = pd.DataFrame([[dt_str_b, loc_b, weather_b, wind_b, 0.0, 0.0, 0.0, surface_temp_b, "データなし", "-", sky_img_name, surf_img_name]], 
                                       columns=REQUIRED_COLUMNS)
                db_container["df"] = pd.concat([db_container["df"], new_row], ignore_index=True)
                st.success(f"【登録完了】 {loc_b} ({dt_str_b}) の天候・表面温度データを保存しました！")
                
            db_container["df"].to_csv(DB_FILE, index=False, encoding="utf-8-sig")
            st.rerun()

# ==========================================
# タブ2: 地点別最新一覧
# ==========================================
with tab2:
    st.header("📋 校内各地点の最新状況")
    
    view_tab_a, view_tab_b = st.tabs(["🌡️ WBGT最新状況", "🌤️ 天候・表面温度最新状況"])
    df = db_container["df"]

    # --- サブタブ1: WBGT最新一覧 ---
    with view_tab_a:
        common_df = df[df["地点"] == "校内全体（全地点共通）"]
        common_sky_img = None
        common_weather_str = "-"
        common_wind_str = "-"
        if not common_df.empty:
            common_row = common_df.iloc[-1]
            common_weather_str = common_row.get("天候", "-")
            common_wind_str = common_row.get("風", "-")
            sky_f = common_row.get("空画像", "-")
            if pd.notna(sky_f) and sky_f != "-" and os.path.exists(os.path.join(IMAGE_DIR, str(sky_f))):
                common_sky_img = os.path.join(IMAGE_DIR, str(sky_f))

        if common_sky_img:
            st.subheader("🌤️ 校内全体の最新の空模様")
            st.image(common_sky_img, caption=f"校内全体の空（天候: {common_weather_str} / 風: {common_wind_str}）", use_container_width=True)
            st.write("---")

        st.subheader("地点別 WBGT最新測定値")

        for idx, loc in enumerate(LOCATIONS_WBGT):
            mapped_target = LOCATION_MAPPING.get(loc, None)
            loc_df = df[(df["地点"] == loc) | (df["地点"] == mapped_target)] if mapped_target else df[df["地点"] == loc]
            
            wbgt_records = loc_df[loc_df["WBGT"] > 0]
            weather_records = loc_df[(loc_df["天候"].notna()) & (loc_df["天候"] != "-")]
            
            with st.container():
                if not wbgt_records.empty or not weather_records.empty:
                    latest_wbgt_row = wbgt_records.iloc[-1] if not wbgt_records.empty else (loc_df.iloc[-1] if not loc_df.empty else None)
                    
                    wbgt_val = latest_wbgt_row.get("WBGT", 0) if latest_wbgt_row is not None else 0
                    judgment_text = latest_wbgt_row.get("判定", "データなし") if latest_wbgt_row is not None else "データなし"
                    ta_val = latest_wbgt_row.get("気温", 0) if latest_wbgt_row is not None else 0
                    rh_val = latest_wbgt_row.get("湿度", 0) if latest_wbgt_row is not None else 0
                    img_file = latest_wbgt_row.get("画像", "-") if latest_wbgt_row is not None else "-"
                    wbgt_dt_str = str(latest_wbgt_row.get("日時", "")) if latest_wbgt_row is not None else ""
                    
                    weather_val = "-"
                    wind_val = "-"
                    sky_img_file = "-"
                    surf_img_file = "-"
                    
                    if not weather_records.empty:
                        latest_weather_row = weather_records.iloc[-1]
                        weather_val = latest_weather_row.get("天候", "-")
                        wind_val = latest_weather_row.get("風", "-")
                        sky_img_file = latest_weather_row.get("空画像", "-")
                        surf_img_file = latest_weather_row.get("表面画像", "-")
                    elif loc in REFLECT_WEATHER_LOCATIONS:
                        weather_val = common_weather_str
                        wind_val = common_wind_str
                        if not common_df.empty:
                            sky_img_file = common_df.iloc[-1].get("空画像", "-")

                    disp_dt = wbgt_dt_str[5:16].replace('-', '/') if len(wbgt_dt_str) >= 16 else wbgt_dt_str
                    _, color = judge_wbgt(wbgt_val) if (isinstance(wbgt_val, (int, float)) and wbgt_val > 0) else ("データなし", "#BDC3C7")
                    
                    wbgt_disp = f"{wbgt_val:.1f}℃" if isinstance(wbgt_val, (int, float)) and wbgt_val > 0 else "-"
                    ta_disp = f"{ta_val:.1f}℃" if isinstance(ta_val, (int, float)) and ta_val > 0 else "-"
                    rh_disp = f"{rh_val:.1f}%" if isinstance(rh_val, (int, float)) and rh_val > 0 else "-"
                    
                    st.markdown(
                        f"""
                        <div style="border-left: 6px solid {color}; padding: 10px 14px; background-color: #f8f9fa; border-radius: 6px; box-shadow: 1px 1px 3px rgba(0,0,0,0.05); margin-bottom: 6px;">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <span style="font-size: 1.05rem; font-weight: bold; color: #333;">📍 {loc}</span>
                                <span style="background-color: {color}; color: white; padding: 2px 10px; border-radius: 50px; font-weight: bold; font-size: 0.88rem;">{judgment_text}</span>
                            </div>
                            <div style="display: flex; flex-wrap: wrap; gap: 12px 16px; margin-top: 8px; font-size: 0.9rem; color: #333;">
                                <span><b>WBGT:</b> <span style="color:{color}; font-weight:bold; font-size:1.1rem;">{wbgt_disp}</span></span>
                                <span><b>気温:</b> {ta_disp}</span>
                                <span><b>湿度:</b> {rh_disp}</span>
                                <span><b>天候:</b> {weather_val}</span>
                                <span><b>風:</b> {wind_val}</span>
                                <span style="margin-left: auto; color: #888; font-weight: bold; font-size: 0.8rem;">📅 最終測定: {disp_dt}</span>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                    
                    has_sky = pd.notna(sky_img_file) and sky_img_file != "-" and os.path.exists(os.path.join(IMAGE_DIR, str(sky_img_file)))
                    has_main = pd.notna(img_file) and img_file != "-" and os.path.exists(os.path.join(IMAGE_DIR, str(img_file)))
                    has_surf = pd.notna(surf_img_file) and surf_img_file != "-" and os.path.exists(os.path.join(IMAGE_DIR, str(surf_img_file)))
                    
                    btn_cols = st.columns([1, 1, 1, 2])
                    if has_sky:
                        with btn_cols[0]:
                            if st.button("🌤️ 空の写真を見る", key=f"btn_modal_sky_{idx}"):
                                show_image_modal(os.path.join(IMAGE_DIR, str(sky_img_file)), f"{loc} - 空の様子")
                    if has_main:
                        with btn_cols[1]:
                            if st.button("📷 機器写真を見る", key=f"btn_modal_main_{idx}"):
                                show_image_modal(os.path.join(IMAGE_DIR, str(img_file)), f"{loc} - 測定機器")
                    if has_surf:
                        with btn_cols[2]:
                            if st.button("🌡️ 表面温度写真", key=f"btn_modal_surf_{idx}"):
                                show_image_modal(os.path.join(IMAGE_DIR, str(surf_img_file)), f"{loc} - 地面表面温度")

                    st.write("")
                else:
                    st.markdown(
                        f"""
                        <div style="border-left: 6px solid #BDC3C7; padding: 8px 12px; margin-bottom: 6px; background-color: #f8f9fa; border-radius: 4px;">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <span style="font-size: 1rem; font-weight: bold; color: #7f8c8d;">📍 {loc}</span>
                                <span style="background-color: #BDC3C7; color: white; padding: 2px 10px; border-radius: 50px; font-weight: bold; font-size: 0.8rem;">データなし</span>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

    # --- サブタブ2: 天候・表面温度最新一覧 ---
    with view_tab_b:
        st.subheader("校内天候・地面表面温度の最新情報")
        for idx, loc in enumerate(LOCATIONS_ENV):
            mapped_target = LOCATION_MAPPING.get(loc, None)
            loc_df = df[(df["地点"] == loc) | (df["地点"] == mapped_target)] if mapped_target else df[df["地点"] == loc]
            
            weather_records = loc_df[(loc_df["天候"].notna()) & (loc_df["天候"] != "-")]
            
            with st.container():
                if not weather_records.empty:
                    latest_row = weather_records.iloc[-1]
                    weather_val = latest_row.get("天候", "-")
                    wind_val = latest_row.get("風", "-")
                    surf_val = latest_row.get("表面温度", "-")
                    sky_img_file = latest_row.get("空画像", "-")
                    surf_img_file = latest_row.get("表面画像", "-")
                    
                    raw_dt_str = str(latest_row.get("日時", ""))
                    formatted_dt_str = raw_dt_str[5:16].replace('-', '/') if len(raw_dt_str) >= 16 else raw_dt_str
                    surf_disp = f"{surf_val:.1f}℃" if isinstance(surf_val, (int, float)) else f"{surf_val}"
                    
                    st.markdown(
                        f"""
                        <div style="border-left: 6px solid #2ECC71; padding: 8px 12px; margin-bottom: 4px; background-color: #f8f9fa; border-radius: 4px; box-shadow: 1px 1px 2px rgba(0,0,0,0.05);">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <span style="font-size: 1rem; font-weight: bold; color: #333;">📍 {loc}</span>
                                <span style="color: #888; font-weight: bold; font-size: 0.8rem;">📅 {formatted_dt_str}</span>
                            </div>
                            <div style="display: flex; flex-wrap: wrap; gap: 16px; margin-top: 6px; font-size: 0.85rem; color: #444;">
                                <span><b>天候:</b> {weather_val}</span>
                                <span><b>風:</b> {wind_val}</span>
                                <span><b>地面表面温度:</b> <span style="color:#D35400; font-weight:bold;">{surf_disp}</span></span>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                    
                    has_sky = pd.notna(sky_img_file) and sky_img_file != "-" and os.path.exists(os.path.join(IMAGE_DIR, str(sky_img_file)))
                    has_surf = pd.notna(surf_img_file) and surf_img_file != "-" and os.path.exists(os.path.join(IMAGE_DIR, str(surf_img_file)))
                    
                    btn_cols_env = st.columns([1, 1, 2])
                    if has_sky:
                        with btn_cols_env[0]:
                            if st.button("🌤️ 空の写真を見る", key=f"btn_env_modal_sky_{idx}"):
                                show_image_modal(os.path.join(IMAGE_DIR, str(sky_img_file)), f"{loc} - 空の様子")
                    if has_surf:
                        with btn_cols_env[1]:
                            if st.button("🌡️ 表面温度写真を見る", key=f"btn_env_modal_surf_{idx}"):
                                show_image_modal(os.path.join(IMAGE_DIR, str(surf_img_file)), f"{loc} - 表面温度")
                    st.write("")
                else:
                    st.markdown(
                        f"""
                        <div style="border-left: 6px solid #BDC3C7; padding: 6px 12px; margin-bottom: 6px; background-color: #f8f9fa; border-radius: 4px;">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <span style="font-size: 1rem; font-weight: bold; color: #7f8c8d;">📍 {loc}</span>
                                <span style="background-color: #BDC3C7; color: white; padding: 2px 10px; border-radius: 50px; font-weight: bold; font-size: 0.8rem;">データなし</span>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

# ==========================================
# タブ3: 全履歴（CSV）＆ 消去機能
# ==========================================
with tab3:
    st.header("📊 過去の全データ記録・管理")
    df = db_container["df"]
    
    if not df.empty:
        with st.expander("🗑️ 不要なデータを消去・削除する"):
            st.warning("※選択した行のデータが完全に削除されます。")
            
            delete_options = [f"ID {i}: [{row['日時']}] {row['地点']} (WBGT:{row['WBGT']} / 天候:{row['天候']})" for i, row in df.iterrows()]
            selected_to_delete = st.selectbox("削除するデータを選択してください", delete_options, index=len(delete_options)-1)
            
            if st.button("選択したデータを削除する", type="secondary"):
                target_idx = int(selected_to_delete.split(":")[0].replace("ID ", ""))
                
                db_container["df"] = db_container["df"].drop(index=target_idx).reset_index(drop=True)
                db_container["df"].to_csv(DB_FILE, index=False, encoding="utf-8-sig")
                
                st.success("データを正常に削除しました！")
                st.rerun()

        st.write("---")
        st.dataframe(df.iloc[::-1], use_container_width=True)
        csv_data = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("これまでの全データをCSVで保存", data=csv_data, file_name="wbgt_history_all.csv", mime="text/csv")
    else:
        st.info("登録されたデータはまだありません。")
