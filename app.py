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
# タブ1: 新規登録（小タブで分帳）
# ==========================================
with tab1:
    st.header("新規データの登録")
    
    # 登録フォームをさらに2つのサブタブに分離
    sub_tab_a, sub_tab_b = st.tabs(["🌡️ WBGT・測定値登録", "🌤️ 天候・空写真登録"])
    
    # --- サブタブA: 測定値の入力 ---
    with sub_tab_a:
        st.subheader("1. 測定値の入力")
        loc_a = st.selectbox("観測地点を選択", LOCATIONS, key="loc_a")
        
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
            
            new_row = pd.DataFrame([[dt_str_a, loc_a, "-", "-", wbgt_a, ta_a, rh_a, judgment, img_name, "-"]], 
                                   columns=["日時", "地点", "天候", "風", "WBGT", "気温", "湿度", "判定", "画像", "空画像"])
            
            db_container["df"] = pd.concat([db_container["df"], new_row], ignore_index=True)
            db_container["df"].to_csv(DB_FILE, index=False, encoding="utf-8-sig")
            st.success(f"【登録完了】 {loc_a} の測定データを保存しました！")
            st.rerun()

    # --- サブタブB: 天候・空写真の登録 ---
    with sub_tab_b:
        st.subheader("2. 天候・環境データの入力")
        st.info("※事前に測定値を登録していなくても、天候データ単体（または最新データへの追記）として保存できます。")
        
        loc_b = st.selectbox("観測地点を選択", LOCATIONS, key="loc_b")
        
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
        uploaded_sky_b = st.file_uploader("🌤️ 空の写真（任意）", type=["jpg", "jpeg", "png"], key="sky_b")
        
        if st.button("天候データを登録・更新する", type="primary", key="btn_b"):
            try:
                datetime.strptime(dt_str_b, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                st.error("時刻の入力形式が正しくありません。「15:30」のように入力してください。")
                st.stop()
                
            dt_stamp = f"{date_b.strftime('%Y%m%d')}_{time_part_b.replace(':', '')}"
            sky_img_name = save_uploaded_image(uploaded_sky_b, "sky", dt_stamp, loc_b)
            
            df = db_container["df"]
            # 同一地点かつ同一日時のデータがあれば更新、なければ新規作成
            match_mask = (df["地点"] == loc_b) & (df["日時"] == dt_str_b)
            
            if not df[match_mask].empty:
                # 既存データに天候・風・空写真を上書き追加
                idx = df[match_mask].index[-1]
                db_container["df"].loc[idx, "天候"] = weather_b
                db_container["df"].loc[idx, "風"] = wind_b
                if sky_img_name != "-":
                    db_container["df"].loc[idx, "空画像"] = sky_img_name
                st.success(f"【更新完了】 {loc_b} ({dt_str_b}) の天候情報を紐付けました！")
            else:
                # 単体として新規追加
                new_row = pd.DataFrame([[dt_str_b, loc_b, weather_b, wind_b, 0.0, 0.0, 0.0, "データなし", "-", sky_img_name]], 
                                       columns=["日時", "地点", "天候", "風", "WBGT", "気温", "湿度", "判定", "画像", "空画像"])
                db_container["df"] = pd.concat([db_container["df"], new_row], ignore_index=True)
                st.success(f"【登録完了】 {loc_b} の天候データを新規保存しました！")
                
            db_container["df"].to_csv(DB_FILE, index=False, encoding="utf-8-sig")
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
                
                raw_dt_str = str(latest_row['日時'])
                formatted_dt_str = raw_dt_str[5:16].replace('-', '/') if len(raw_dt_str) >= 16 else raw_dt_str
                
                _, color = judge_wbgt(wbgt_val) if wbgt_val > 0 else ("データなし", "#BDC3C7")
                
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
                            <span style="margin-left: auto; color: #888; font-weight: bold;">📅 {formatted_dt_str}</span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                
                # 写真ボタンの表示
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
