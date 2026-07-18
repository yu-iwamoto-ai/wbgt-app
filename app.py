# -*- coding: utf-8 -*-
import streamlit as st
import os
import pandas as pd
from datetime import datetime

# ページの設定
st.set_page_config(page_title="校内WBGT観測", page_icon="🌡️", layout="centered")

# フォルダの準備
IMAGE_DIR = "saved_images"
os.makedirs(IMAGE_DIR, exist_ok=True)

# 簡易データベース（CSVファイル）の準備
DB_FILE = "wbgt_data.csv"
if not os.path.exists(DB_FILE):
    df_init = pd.DataFrame(columns=["日時", "地点", "WBGT", "気温", "湿度", "判定", "画像"])
    df_init.to_csv(DB_FILE, index=False, encoding="utf-8-sig")

# 熱中症判定のルール
def judge_wbgt(val):
    if val >= 31: return "🔴 危険"
    elif val >= 28: return "🔶 厳重警戒"
    elif val >= 25: return "💛 警戒"
    else: return "🔹 注意"

st.title("🌡️ 校内WBGT観測（かんたん版）")

tab1, tab2 = st.tabs(["📸 新規登録", "📋 履歴一覧"])

with tab1:
    st.header("1. 測定値の入力")
    
    # 入力項目
    location = st.selectbox("観測地点", ["体育館", "校庭", "テニスコート", "武道場", "その他"])
    wbgt = st.number_input("WBGT (℃)", value=25.0, step=0.1, format="%.1f")
    ta = st.number_input("気温 (℃)", value=30.0, step=0.1, format="%.1f")
    rh = st.number_input("湿度 (%)", value=60.0, step=0.1, format="%.1f")
    
    # 写真の添付（保存用）
    uploaded_file = st.file_uploader("証拠写真をアップロード（任意）", type=["jpg", "jpeg", "png"])
    
    # 登録ボタン
    if st.button("この内容で登録する", type="primary"):
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        judgment = judge_wbgt(wbgt)
        img_name = "-"
        
        # 画像があれば保存
        if uploaded_file is not None:
            img_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{location}.jpg"
            with open(os.path.join(IMAGE_DIR, img_name), "wb") as f:
                f.write(uploaded_file.getbuffer())
        
        # CSVに追加保存
        new_data = pd.DataFrame([[now_str, location, wbgt, ta, rh, judgment, img_name]], 
                                columns=["日時", "地点", "WBGT", "気温", "湿度", "判定", "画像"])
        new_data.to_csv(DB_FILE, mode="a", header=False, index=False, encoding="utf-8-sig")
        
        st.success(f"【登録完了】 {location} のデータを保存しました！")
        st.balloons()

with tab2:
    st.header("📋 これまでの記録")
    if os.path.exists(DB_FILE):
        df = pd.read_csv(DB_FILE, encoding="utf-8-sig")
        if not df.empty:
            st.dataframe(df.iloc[::-1], use_container_width=True) # 新しい順に表示
            
            # CSVダウンロード
            csv_data = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("データをCSVでダウンロード", data=csv_data, file_name="wbgt_history.csv", mime="text/csv")
        else:
            st.info("登録されたデータはまだありません。")
