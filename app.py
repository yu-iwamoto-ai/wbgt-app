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

# 🔥 24時間（86400秒）データを保持するメモリ空間
@st.cache_resource(ttl=86400)
def get_secure_database():
    return {"df": pd.DataFrame(columns=["日時", "地点", "WBGT", "気温", "湿度", "判定", "画像"])}

db_container = get_secure_database()

# ファイルとしてのバックアップ準備
DB_FILE = "wbgt_data.csv"
if not os.path.exists(DB_FILE):
    df_init = pd.DataFrame(columns=["日時", "地点", "WBGT", "気温", "湿度", "判定", "画像"])
    df_init.to_csv(DB_FILE, index=False, encoding="utf-8-sig")
else:
    try:
        file_df = pd.read_csv(DB_FILE, encoding="utf-8-sig")
        if not file_df.empty and db_container["df"].empty:
            db_container["df"] = file_df
    except:
        pass

# 🔥 【重要】熱中症判定のルール（33℃以上の紫を追加した5段階）
def judge_wbgt(val):
    if val >= 33: return "🟣 危険（熱中症警戒アラート）", "#800080"
    elif val >= 31: return "🔴 危険", "#FF4B4B"
    elif val >= 28: return "🔶 厳重警戒", "#FFA500"
    elif val >= 25: return "💛 警戒", "#F1C40F"
    else: return "🔹 注意", "#3498DB"

st.title("🌡️ 校内WBGT観測システム")
st.caption("手入力 ＋ 写真保存版（熱中症警戒アラート対応モード）")

tab1, tab2, tab3 = st.tabs(["📸 新規登録", "📋 地点別最新一覧", "📊 全履歴（CSV）"])

# ==========================================
# タブ1: 新規登録
# ==========================================
with tab1:
    st.header("1. 測定値と日時の入力")
    
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
    
    wbgt = st.number_input("WBGT (℃)", value=25.0, step=0.1, format="%.1f")
    ta = st.number_input("気温 (℃)", value=30.0, step=0.1, format="%.1f")
    rh = st.number_input("湿度 (%)", value=60.0, step=0.1, format="%.1f")
    
    uploaded_file = st.file_uploader("証拠写真をアップロード（任意）", type=["jpg", "jpeg", "png"])
    
    if st.button("この内容で登録する", type="primary"):
        try:
            datetime.strptime(selected_datetime_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            st.error("時刻の入力形式が正しくありません。「15:30」のように半角のコロンで区切って入力してください。")
            st.stop()

        judgment, _ = judge_wbgt(wbgt)
        img_name = "-"
        
        if uploaded_file is not None:
            time_for_file = time_part.replace(":", "")
            img_name = f"{input_date.strftime('%Y%m%d')}_{time_for_file}_{location}.jpg"
            
            try:
                image = Image.open(uploaded_file)
                image = ImageOps.exif_transpose(image)
                image.save(os.path.join(IMAGE_DIR, img_name), "JPEG", quality=85)
            except Exception as e:
                with open(os.path.join(IMAGE_DIR, img_name), "wb") as f:
                    f.write(uploaded_file.getbuffer())
        
        new_row = pd.DataFrame([[selected_datetime_str, location, wbgt, ta, rh, judgment, img_name]], 
                               columns=["日時", "地点", "WBGT", "気温", "湿度", "判定", "画像"])
        
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
                img_file = latest_row["画像"] if "画像" in latest_row else "-"
                
                _, color = judge_wbgt(wbgt_val)
                
                st.markdown(
                    f"""
                    <div style="border-left: 6px solid {color}; padding: 6px 12px; margin-bottom: 4px; background-color: #f8f9fa; border-radius: 4px; box-shadow: 1px 1px 2px rgba(0,0,0,0.05);">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span style="font-size: 1rem; font-weight: bold; color: #333;">📍 {loc}</span>
                            <span style="background-color: {color}; color: white; padding: 2px 10px; border-radius: 50px; font-weight: bold; font-size: 0.8rem;">{judgment_text}</span>
                        </div>
                        <div style="display: flex; gap: 15px; margin-top: 4px; font-size: 0.85rem; color: #444;">
                            <span><b>WBGT:</b> <span style="color:{color}; font-weight:bold;">{wbgt_val:.1f}℃</span></span>
                            <span><b>気温:</b> {latest_row['気温']:.1f}℃</span>
                            <span><b>湿度:</b> {latest_row['湿度']:.1f}%</span>
                            <span style="font-size: 0.75rem; color: #888; margin-left: auto;">🕒 {latest_row['日時'][11:16]}</span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                
                if pd.notna(img_file) and img_file != "-":
                    img_path = os.path.join(IMAGE_DIR, img_file)
                    if os.path.exists(img_path):
                        with st.expander("📸 証拠写真を表示"):
                            st.image(img_path, caption=f"{loc} の測定写真", use_container_width=True)
                
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
