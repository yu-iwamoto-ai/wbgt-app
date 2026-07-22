# -*- coding: utf-8 -*-
import streamlit as st
import os
import pandas as pd
from datetime import datetime, date
from PIL import Image, ImageOps

# ページの設定
st.set_page_config(page_title="校内WBGT観測システム", page_icon="🌡️", layout="centered")

# フォルダと5地点の設定
IMAGE_DIR = "saved_images"
os.makedirs(IMAGE_DIR, exist_ok=True)
LOCATIONS = ["講堂", "柏倫館", "エントランス", "東門付近", "西館3F"]
WEATHERS = ["晴れ ☀️", "曇り ☁️", "雨 🌧️", "室内 🏢"]
WINDS = ["なし 🍃", "弱風 🌬️", "強風 💨"]

# 24時間（86400秒）データを保持するメモリ空間
@st.cache_resource(ttl=86400)
def get_secure_database():
    return {"df": pd.DataFrame(columns=["日時", "地点", "天候", "風", "WBGT", "気温", "湿度", "判定", "画像", "空画像"])}

db_container = get_secure_database()

# ファイルとしてのバックアップ準備
DB_FILE = "wbgt_data.csv"
if not os.path.exists(DB_FILE):
    df_init = pd.DataFrame(columns=["日時", "地点", "天候", "風", "WBGT", "気温", "湿度", "判定", "画像", "空画像"])
    df_init.to_csv(DB_FILE, index=False, encoding="utf-8-sig")
else:
    try:
        file_df = pd.read_csv(DB_FILE, encoding="utf-8-sig")
        if not file_df.empty and db_container["df"].empty:
            db_container["df"] = file_df
    except:
        pass

# 熱中症判定のルール（33℃以上の紫を含めた5段階）
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

st.title("🌡️ 校内WBGT観測システム")
st.caption("手入力 ＋ W写真保存（機器・空）＋ 天候観測モード")

tab1, tab2, tab3 = st.tabs(["📸 新規登録", "📋 地点別最新一覧", "📊 全履歴（CSV）"])

# ==========================================
# タブ1: 新規登録
# ==========================================
with tab1:
    st.header("1. 測定値と環境の入力")
    
    location = st.selectbox("観測地点を選択", LOCATIONS)
    
    c_date, c_time = st.columns(2)
    with c_date:
        input_date = st.date_input("観測日を選択", date.today())
    with c_time:
        now_time_str = datetime.now().strftime("%H:%M")
        input_time_str = st.text_input("観測時刻（直接入力用）", value=now_time_str, help="例: 15:30")
    
    time_part = input_time_str.strip()
    if len(time_part) == 5:
        time_part += ":00"
    elif len(time_part) == 4 and ":" in time_part:
        time_part = "0" + time_part + ":00"
        
    selected_datetime_str = f"{input_date} {time_part}"
    
    st.write("---")
    
    c_weather, c_wind = st.columns(2)
    with c_weather:
        weather = st.selectbox("天候を選択", WEATHERS)
    with c_wind:
        wind = st.selectbox("風の有無を選択", WINDS)
        
    st.write("---")
    
    wbgt = st.number_input("WBGT (℃)", value=25.0, step=0.1, format="%.1f")
    ta = st.number_input("気温 (℃)", value=30.0, step=0.1, format="%.1f")
    rh = st.number_input("湿度 (%)", value=60.0, step=0.1, format="%.1f")
    
    st.write("---")
    st.subheader("📷 写真の添付（任意）")
    c_img1, c_img2 = st.columns(2)
    with c_img1:
        uploaded_file = st.file_uploader("1. 測定機器の証拠写真", type=["jpg", "jpeg", "png"], key="main_img")
    with c_img2:
        uploaded_sky_file = st.file_uploader("2. 空の写真（天候確認用）", type=["jpg", "jpeg", "png"], key="sky_img")
    
    if st.button("この内容で登録する", type="primary"):
        try:
            datetime.strptime(selected_datetime_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            st.error("時刻の入力形式が正しくありません。「15:30」のように半角のコロンで区切って入力してください。")
            st.stop()

        judgment, _ = judge_wbgt(wbgt)
        
        # ファイル名用の日時文字列を作成
        date_for_file = input_date.strftime('%Y%m%d')
        time_for_file = time_part.replace(":", "")
        dt_stamp = f"{date_for_file}_{time_for_file}"
        
        # 2種類の画像をそれぞれ保存
        img_name = save_uploaded_image(uploaded_file, "main", dt_stamp, location)
        sky_img_name = save_uploaded_image(uploaded_sky_file, "sky", dt_stamp, location)
        
        new_row = pd.DataFrame([[selected_datetime_str, location, weather, wind, wbgt, ta, rh, judgment, img_name, sky_img_name]], 
                               columns=["日時", "地点", "天候", "風", "WBGT", "気温", "湿度", "判定", "画像", "空画像"])
        
        db_container["df"] = pd.concat([db_container["df"], new_row], ignore_index=True)
        db_container["df"].to_csv(DB_FILE, index=False, encoding="utf-8-sig")
        
        st.success(f"【登録完了】 {location} のデータを保存しました！")
        st.rerun()

# ==========================================
# タブ2: 地点別最新一覧
# ==========================================
with tab2:
    st.header("📋 校内各地点の最新状況")
    
    df = db_container["df"]
    
    for loc in LOCATIONS:
        loc_df = df[df["地点"] == loc]
        
        with st.container():
            if not loc_df.empty:
                latest_row = loc_df.iloc[-1]
                judgment_text = latest_row["判定"]
                wbgt_val = latest_row["WBGT"]
                
                weather_val = latest_row["天候"] if "天候" in latest_row and pd.notna(latest_row["天候"]) else "-"
                wind_val = latest_row["風"] if "風" in latest_row and pd.notna(latest_row["風"]) else "-"
                img_file = latest_row["画像"] if "画像" in latest_row else "-"
                sky_img_file = latest_row["空画像"] if "空画像" in latest_row else "-"
                
                _, color = judge_wbgt(wbgt_val)
                
                st.markdown(
                    f"""
                    <div style="border-left: 6px solid {color}; padding: 8px 12px; margin-bottom: 4px; background-color: #f8f9fa; border-radius: 4px; box-shadow: 1px 1px 2px rgba(0,0,0,0.05);">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span style="font-size: 1rem; font-weight: bold; color: #333;">📍 {loc}</span>
                            <span style="background-color: {color}; color: white; padding: 2px 10px; border-radius: 50px; font-weight: bold; font-size: 0.8rem;">{judgment_text}</span>
                        </div>
                        <div style="display: flex; flex-wrap: wrap; gap: 12px; margin-top: 6px; font-size: 0.85rem; color: #444;">
                            <span><b>WBGT:</b> <span style="color:{color}; font-weight:bold;">{wbgt_val:.1f}℃</span></span>
                            <span><b>気温:</b> {latest_row['気温']:.1f}℃</span>
                            <span><b>湿度:</b> {latest_row['湿度']:.1f}%</span>
                        </div>
                        <div style="display: flex; gap: 12px; margin-top: 4px; font-size: 0.8rem; color: #666;">
                            <span><b>天候:</b> {weather_val}</span>
                            <span><b>風:</b> {wind_val}</span>
                            <span style="margin-left: auto; color: #888;">🕒 {latest_row['日時'][11:16]}</span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                
                # 写真ボタンの表示（押したらパッと見られます）
                has_main = pd.notna(img_file) and img_file != "-" and os.path.exists(os.path.join(IMAGE_DIR, img_file))
                has_sky = pd.notna(sky_img_file) and sky_img_file != "-" and os.path.exists(os.path.join(IMAGE_DIR, sky_img_file))
                
                if has_main or has_sky:
                    c_btn1, c_btn2 = st.columns(2)
                    if has_main:
                        with c_btn1:
                            with st.expander("📸 機器の写真"):
                                st.image(os.path.join(IMAGE_DIR, img_file), caption=f"{loc} の測定機器写真", use_container_width=True)
                    if has_sky:
                        with c_btn2:
                            with st.expander("🌤️ 空の写真"):
                                st.image(os.path.join(IMAGE_DIR, sky_img_file), caption=f"{loc} の空の写真", use_container_width=True)
                
                st.write("")
            else:
                st.markdown(
                    """
                    <div style="border-left: 6px solid #BDC3C7; padding: 6px 12px; margin-bottom: 6px; background-color: #f8f9fa; border-radius: 4px;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span style="font-size: 1rem; font-weight: bold; color: #7f8c8d;">📍 {loc}</span>
                            <span style="background-color: #BDC3C7; color: white; padding: 2px 10px; border-radius: 50px; font-weight: bold; font-size: 0.8rem;">データなし</span>
                        </div>
                    </div>
                    """.format(loc=loc),
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
