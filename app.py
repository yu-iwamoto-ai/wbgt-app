# -*- coding: utf-8 -*-
import streamlit as st
import os
import pandas as pd
from datetime import datetime, date
from PIL import Image, ImageOps

# ページの設定
st.set_page_config(page_title="校内WBGT観測システム", page_icon="🌡️", layout="centered")

# フォルダの設定
IMAGE_DIR = "saved_images"
os.makedirs(IMAGE_DIR, exist_ok=True)

# 地点設定
LOCATIONS_WBGT = ["講堂", "柏倫館", "エントランス", "東門付近", "西館3F"]
LOCATIONS_ENV = ["校内全体（全地点共通）", "正門付近", "東門付近", "グラウンド", "南館屋上", "建学の庭付近"]

# 「エントランス」と「正門付近」の紐付け定義
LOCATION_MAPPING = {
    "エントランス": "正門付近",
    "正門付近": "エントランス"
}

WEATHERS = ["晴れ ☀️", "曇り ☁️", "雨 🌧️", "室内 🏢"]
WINDS = ["なし 🍃", "弱風 🌬️", "強風 💨"]

# データを保持するメモリ空間
@st.cache_resource(ttl=86400)
def get_secure_database():
    return {"df": pd.DataFrame(columns=["日時", "地点", "天候", "風", "WBGT", "気温", "湿度", "表面温度", "判定", "画像", "空画像", "表面画像"])}

db_container = get_secure_database()

# CSVファイルバックアップ準備
DB_FILE = "wbgt_data.csv"
if not os.path.exists(DB_FILE):
    df_init = pd.DataFrame(columns=["日時", "地点", "天候", "風", "WBGT", "気温", "湿度", "表面温度", "判定", "画像", "空画像", "表面画像"])
    df_init.to_csv(DB_FILE, index=False, encoding="utf-8-sig")
else:
    try:
        file_df = pd.read_csv(DB_FILE, encoding="utf-8-sig")
        for col in ["天候", "風", "表面温度", "画像", "空画像", "表面画像"]:
            if col not in file_df.columns:
                file_df[col] = "-"
        if not file_df.empty and db_container["df"].empty:
            db_container["df"] = file_df
    except:
        pass

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

st.title("🌡️ 校内WBGT・環境観測システム")
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
            mapped_loc = LOCATION_MAPPING.get(loc_a, None)
            
            # 自地点、ペア地点、または「校内全体」の同一日時データを探す
            match_mask = (df["日時"] == dt_str_a) & ((df["地点"] == loc_a) | (df["地点"] == mapped_loc) | (df["地点"] == "校内全体（全地点共通）"))
            
            if not df[match_mask].empty:
                idx = df[match_mask].index[-1]
                db_container["df"].loc[idx, "地点"] = loc_a  # 地点を設定
                db_container["df"].loc[idx, "WBGT"] = wbgt_a
                db_container["df"].loc[idx, "気温"] = ta_a
                db_container["df"].loc[idx, "湿度"] = rh_a
                db_container["df"].loc[idx, "判定"] = judgment
                if img_name != "-":
                    db_container["df"].loc[idx, "画像"] = img_name
                st.success(f"【更新完了】 {loc_a} ({dt_str_a}) の測定データを更新・紐付けました！")
            else:
                new_row = pd.DataFrame([[dt_str_a, loc_a, "-", "-", wbgt_a, ta_a, rh_a, "-", judgment, img_name, "-", "-"]], 
                                       columns=["日時", "地点", "天候", "風", "WBGT", "気温", "湿度", "表面温度", "判定", "画像", "空画像", "表面画像"])
                db_container["df"] = pd.concat([db_container["df"], new_row], ignore_index=True)
                st.success(f"【登録完了】 {loc_a} の測定データを保存しました！")
                
            db_container["df"].to_csv(DB_FILE, index=False, encoding="utf-8-sig")
            st.rerun()

    # --- サブタブB: 天候・表面温度の入力 ---
    with sub_tab_b:
        st.subheader("2. 天候・地面の表面温度データの入力")
        loc_b = st.selectbox("対象を選択", LOCATIONS_ENV, key="loc_b", help="「校内全体（全地点共通）」を選ぶと全地点のWBGT表示に天候が反映されます")
        
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
            mapped_loc = LOCATION_MAPPING.get(loc_b, None)
            
            # 自地点または紐付けペア地点で同一日時のデータを探す
            match_mask = (df["日時"] == dt_str_b) & ((df["地点"] == loc_b) | (df["地点"] == mapped_loc))
            
            if not df[match_mask].empty:
                idx = df[match_mask].index[-1]
                db_container["df"].loc[idx, "天候"] = weather_b
                db_container["df"].loc[idx, "風"] = wind_b
                db_container["df"].loc[idx, "表面温度"] = surface_temp_b
                if sky_img_name != "-": db_container["df"].loc[idx, "空画像"] = sky_img_name
                if surf_img_name != "-": db_container["df"].loc[idx, "表面画像"] = surf_img_name
                st.success(f"【更新完了】 {loc_b} ({dt_str_b}) の天候情報を更新・紐付けました！")
            else:
                new_row = pd.DataFrame([[dt_str_b, loc_b, weather_b, wind_b, 0.0, 0.0, 0.0, surface_temp_b, "データなし", "-", sky_img_name, surf_img_name]], 
                                       columns=["日時", "地点", "天候", "風", "WBGT", "気温", "湿度", "表面温度", "判定", "画像", "空画像", "表面画像"])
                db_container["df"] = pd.concat([db_container["df"], new_row], ignore_index=True)
                st.success(f"【登録完了】 {loc_b} の天候・表面温度データを保存しました！")
                
            db_container["df"].to_csv(DB_FILE, index=False, encoding="utf-8-sig")
            st.rerun()

# ==========================================
# タブ2: 地点別最新一覧
# ==========================================
with tab2:
    st.header("📋 校内各地点の最新状況")
    
    view_tab_a, view_tab_b = st.tabs(["🌡️ WBGT最新状況", "🌤️ 天候・表面温度最新状況"])
    df = db_container["df"]

    # 最新天候情報（校内共通データまたは最新の登録）を取得する関数
    def get_latest_common_weather():
        common_df = df[df["地点"] == "校内全体（全地点共通）"]
        if not common_df.empty:
            return common_df.iloc[-1]
        # なければ直近で「天候」が入力されている行を取得
        valid_weather_df = df[df["天候"].notna() & (df["天候"] != "-")]
        return valid_weather_df.iloc[-1] if not valid_weather_df.empty else None

    # --- サブタブ1: WBGT最新一覧 ---
    with view_tab_a:
        st.subheader("校内WBGT測定値の最新情報")
        common_weather_row = get_latest_common_weather()

        for loc in LOCATIONS_WBGT:
            mapped_target = LOCATION_MAPPING.get(loc, None)
            loc_df = df[(df["地点"] == loc) | (df["地点"] == mapped_target)] if mapped_target else df[df["地点"] == loc]
            
            with st.container():
                if not loc_df.empty:
                    latest_row = loc_df.iloc[-1]
                    judgment_text = latest_row["判定"]
                    wbgt_val = latest_row["WBGT"]
                    
                    # 天候・風の補完（データになければ校内共通天候を使用）
                    weather_val = latest_row["天候"] if ("天候" in latest_row and pd.notna(latest_row["天候"]) and latest_row["天候"] != "-") else (common_weather_row["天候"] if common_weather_row is not None else "-")
                    wind_val = latest_row["風"] if ("風" in latest_row and pd.notna(latest_row["風"]) and latest_row["風"] != "-") else (common_weather_row["風"] if common_weather_row is not None else "-")
                    
                    img_file = latest_row["画像"] if "画像" in latest_row else "-"
                    sky_img_file = latest_row["空画像"] if "空画像" in latest_row else "-"
                    surf_img_file = latest_row["表面画像"] if "表面画像" in latest_row else "-"

                    raw_dt_str = str(latest_row['日時'])
                    formatted_dt_str = raw_dt_str[5:16].replace('-', '/') if len(raw_dt_str) >= 16 else raw_dt_str
                    
                    _, color = judge_wbgt(wbgt_val) if (isinstance(wbgt_val, (int, float)) and wbgt_val > 0) else ("データなし", "#BDC3C7")
                    
                    wbgt_disp = f"{wbgt_val:.1f}℃" if isinstance(wbgt_val, (int, float)) and wbgt_val > 0 else "-"
                    ta_disp = f"{latest_row['気温']:.1f}℃" if isinstance(latest_row['気温'], (int, float)) and latest_row['気温'] > 0 else "-"
                    rh_disp = f"{latest_row['湿度']:.1f}%" if isinstance(latest_row['湿度'], (int, float)) and latest_row['湿度'] > 0 else "-"
                    
                    st.markdown(
                        f"""
                        <div style="border-left: 6px solid {color}; padding: 8px 12px; margin-bottom: 4px; background-color: #f8f9fa; border-radius: 4px; box-shadow: 1px 1px 2px rgba(0,0,0,0.05);">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <span style="font-size: 1rem; font-weight: bold; color: #333;">📍 {loc}</span>
                                <span style="background-color: {color}; color: white; padding: 2px 10px; border-radius: 50px; font-weight: bold; font-size: 0.8rem;">{judgment_text}</span>
                            </div>
                            <div style="display: flex; flex-wrap: wrap; gap: 12px; margin-top: 6px; font-size: 0.85rem; color: #444;">
                                <span><b>WBGT:</b> <span style="color:{color}; font-weight:bold;">{wbgt_disp}</span></span>
                                <span><b>気温:</b> {ta_disp}</span>
                                <span><b>湿度:</b> {rh_disp}</span>
                                <span><b>天候:</b> {weather_val}</span>
                                <span><b>風:</b> {wind_val}</span>
                                <span style="margin-left: auto; color: #888; font-weight: bold;">📅 {formatted_dt_str}</span>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                    
                    has_main = pd.notna(img_file) and img_file != "-" and os.path.exists(os.path.join(IMAGE_DIR, img_file))
                    has_sky = pd.notna(sky_img_file) and sky_img_file != "-" and os.path.exists(os.path.join(IMAGE_DIR, sky_img_file))
                    has_surf = pd.notna(surf_img_file) and surf_img_file != "-" and os.path.exists(os.path.join(IMAGE_DIR, surf_img_file))
                    
                    if has_main or has_sky or has_surf:
                        with st.expander("📷 関連画像・写真を表示"):
                            cols = st.columns(3)
                            if has_main:
                                with cols[0]:
                                    st.image(os.path.join(IMAGE_DIR, img_file), caption="機器写真", use_container_width=True)
                            if has_sky:
                                with cols[1]:
                                    st.image(os.path.join(IMAGE_DIR, sky_img_file), caption="空の写真", use_container_width=True)
                            if has_surf:
                                with cols[2]:
                                    st.image(os.path.join(IMAGE_DIR, surf_img_file), caption="表面温度写真", use_container_width=True)
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

    # --- サブタブ2: 天候・表面温度最新一覧 ---
    with view_tab_b:
        st.subheader("校内天候・地面表面温度の最新情報")
        for loc in LOCATIONS_ENV:
            mapped_target = LOCATION_MAPPING.get(loc, None)
            loc_df = df[(df["地点"] == loc) | (df["地点"] == mapped_target)] if mapped_target else df[df["地点"] == loc]
            
            with st.container():
                if not loc_df.empty:
                    latest_row = loc_df.iloc[-1]
                    weather_val = latest_row["天候"] if "天候" in latest_row and pd.notna(latest_row["天候"]) else "-"
                    wind_val = latest_row["風"] if "風" in latest_row and pd.notna(latest_row["風"]) else "-"
                    surf_val = latest_row["表面温度"] if "表面温度" in latest_row and pd.notna(latest_row["表面温度"]) else "-"
                    sky_img_file = latest_row["空画像"] if "空画像" in latest_row else "-"
                    surf_img_file = latest_row["表面画像"] if "表面画像" in latest_row else "-"
                    
                    raw_dt_str = str(latest_row['日時'])
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
                    
                    has_sky = pd.notna(sky_img_file) and sky_img_file != "-" and os.path.exists(os.path.join(IMAGE_DIR, sky_img_file))
                    has_surf = pd.notna(surf_img_file) and surf_img_file != "-" and os.path.exists(os.path.join(IMAGE_DIR, surf_img_file))
                    
                    if has_sky or has_surf:
                        cols = st.columns(2)
                        if has_sky:
                            with cols[0]:
                                with st.expander("🌤️ 空の写真"):
                                    st.image(os.path.join(IMAGE_DIR, sky_img_file), caption=f"{loc} の空の写真", use_container_width=True)
                        if has_surf:
                            with cols[1]:
                                with st.expander("🌡️ 表面温度の写真"):
                                    st.image(os.path.join(IMAGE_DIR, surf_img_file), caption=f"{loc} の表面温度写真", use_container_width=True)
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
# タブ3: 全履歴（CSV）
# ==========================================
with tab3:
    st.header("📊 過去の全データ記録")
    df = db_container["df"]
    if not df.empty:
        st.dataframe(df.iloc[::-1], use_container_width=True)
        csv_data = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("これまでの全データをCSVで保存", data=csv_data, file_name="wbgt_history_all.csv", mime="text/csv")
    else:
        st.info("登録されたデータはまだありません。")
