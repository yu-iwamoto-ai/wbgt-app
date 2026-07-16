# -*- coding: utf-8 -*-
"""
Created on Thu Jul 16 15:19:55 2026

@author: yurie
"""

# app.py
import streamlit as st
st.set_page_config(
    page_title="校内WBGT観測システム",
    page_icon="🌡️",
    layout="centered",
    initial_sidebar_state="collapsed"
)

import os
import cv2
import numpy as np
import pandas as pd
import plotly.express as px
from datetime import datetime
from PIL import Image

import config
import database
import image_processing
import ocr_reader
import validation
import wbgt_rules

# データベース初期化
database.init_db()

# --- タイトル ---
st.title("🌡️ 校内WBGT観測")
st.caption("A&D AD-5695DLB 連携・熱中症アラートシステム")

# --- タブ分け ---
tab1, tab2, tab3, tab4 = st.tabs(["📸 新規観測", "📋 最新一覧", "📊 履歴・グラフ", "💬 Classi用テキスト"])

# ==========================================
# タブ1: 新規観測 (データのアップロードとOCR)
# ==========================================
with tab1:
    st.header("1. 測定値の登録")
    
    # フォーム外のパラメータ選択
    selected_loc = st.selectbox("観測地点を選択", config.LOCATIONS)
    
    # iPhoneカメラ起動用uploader (accept_multiple_files=False)
    uploaded_file = st.file_uploader(
        "WBGT計を撮影するか、画像を選択してください",
        type=["jpg", "jpeg", "png"],
        help="iPhoneのSafariから開くと、その場でカメラ起動して撮影できます"
    )
    
    if uploaded_file is not None:
        st.subheader("アップロード画像確認")
        
        # 1. 向き自動補正とEXIF削除
        clean_pil_img = image_processing.preprocess_uploaded_image(uploaded_file)
        
        # Streamlitでの表示とOpenCV処理用変換
        st.image(clean_pil_img, caption="撮影された写真（自動補正後）", use_container_width=True)
        cv_img = cv2.cvtColor(np.array(clean_pil_img), cv2.COLOR_RGB2BGR)
        
        # 切り抜き領域の決定
        st.info("液晶画面全体の切り出しとOCR解析を行います。")
        
        # 解析実行ボタン
        if st.button("画像を解析する", type="primary"):
            with st.spinner("OCR解析中..."):
                # 各部分を切り抜いて前処理後にOCR
                extracted_data = {}
                for key in ["wbgt", "ta", "rh"]:
                    cropped = image_processing.crop_roi(cv_img, key)
                    preprocessed = image_processing.apply_ocr_preprocessing(cropped)
                    
                    val, status = ocr_reader.read_numeric_value(preprocessed)
                    extracted_data[key] = {
                        "val": val,
                        "status": status,
                        "cropped_img": cropped
                    }
                
                # 解析結果をセッション状態に保存して永続化
                st.session_state["ocr_results"] = extracted_data
                st.session_state["ocr_done"] = True
                
        # 解析結果がある場合、または手動編集フォーム
        if st.session_state.get("ocr_done", False):
            results = st.session_state["ocr_results"]
            
            # 各切り抜きエリアのプレビュー表示
            cols = st.columns(3)
            for idx, key in enumerate(["wbgt", "ta", "rh"]):
                with cols[idx]:
                    title_name = {"wbgt": "WBGT", "ta": "気温(TA)", "rh": "湿度(RH)"}[key]
                    st.write(f"**{title_name}切り抜き**")
                    # RGBに戻して表示
                    crop_rgb = cv2.cvtColor(results[key]["cropped_img"], cv2.COLOR_BGR2RGB)
                    st.image(crop_rgb, use_container_width=True)
                    st.caption(f"OCR検出: {results[key]['val']} ({results[key]['status']})")
            
            st.write("---")
            st.subheader("2. 読み取り数値の最終確認")
            
            # 手動修正用のフォーム
            # デフォルト値にOCR結果をセット
            default_wbgt = results["wbgt"]["val"] if results["wbgt"]["val"] is not None else 0.0
            default_ta = results["ta"]["val"] if results["ta"]["val"] is not None else 0.0
            default_rh = results["rh"]["val"] if results["rh"]["val"] is not None else 0.0
            
            c1, c2, c3 = st.columns(3)
            with c1:
                input_wbgt = st.number_input("WBGT (℃)", value=float(default_wbgt), step=0.1, format="%.1f")
            with c2:
                input_ta = st.number_input("気温 TA (℃)", value=float(default_ta), step=0.1, format="%.1f")
            with c3:
                input_rh = st.number_input("湿度 RH (%)", value=float(default_rh), step=0.1, format="%.1f")
                
            input_time = st.text_input("観測日時", value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            
            # 入力値バリデーション
            errors = validation.validate_input(input_wbgt, input_ta, input_rh)
            
            # 急激な変化の警告チェック
            change_warning = validation.check_sudden_change(selected_loc, input_wbgt, input_ta, input_time)
            
            if errors:
                for err in errors:
                    st.error(err)
            
            if change_warning:
                st.warning(change_warning)
                
            # 確認合意用チェックボックス
            confirmed = st.checkbox("写真と数値を確認しました（チェックを入れると登録できます）")
            
            # 登録処理
            # エラーがある、または未確認の場合は無効化
            register_disabled = len(errors) > 0 or not confirmed
            
            if st.button("この数値で確定して登録", disabled=register_disabled, type="primary"):
                try:
                    # 画像の保存
                    filename = f"{selected_loc}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                    save_path = os.path.join(config.IMAGE_SAVE_DIR, filename)
                    
                    if config.SAVE_ORIGINAL_IMAGE:
                        # 全体画像を保存
                        clean_pil_img.save(save_path, "JPEG")
                    else:
                        # プライバシーに配慮し、液晶切り出し部分をコラージュまたは代表してWBGT部分のみ保存
                        # ここではWBGT, TA, RHを横に結合した状態の画像を検証・監査証跡用として保存します
                        h_min = min(results["wbgt"]["cropped_img"].shape[0], results["ta"]["cropped_img"].shape[0])
                        w_scaled = int(results["wbgt"]["cropped_img"].shape[1] * (h_min / results["wbgt"]["cropped_img"].shape[0]))
                        
                        wbgt_r = cv2.resize(results["wbgt"]["cropped_img"], (w_scaled, h_min))
                        ta_r = cv2.resize(results["ta"]["cropped_img"], (w_scaled, h_min))
                        rh_r = cv2.resize(results["rh"]["cropped_img"], (w_scaled, h_min))
                        
                        combined = np.hstack((wbgt_r, ta_r, rh_r))
                        cv2.imwrite(save_path, combined)
                    
                    # WBGT自動判定
                    judgment = wbgt_rules.judge_wbgt(input_wbgt)
                    
                    # 登録実行
                    database.insert_record(
                        location=selected_loc,
                        observed_at=input_time,
                        wbgt=input_wbgt,
                        ta=input_ta,
                        humidity=input_rh,
                        judgment=judgment,
                        image_filename=filename,
                        ocr_wbgt=str(results["wbgt"]["val"]),
                        ocr_temperature=str(results["ta"]["val"]),
                        ocr_humidity=str(results["rh"]["val"])
                    )
                    
                    st.success(f"【登録完了】 {selected_loc} の観測データを保存しました！")
                    # セッションクリア
                    st.session_state["ocr_done"] = False
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"データベース登録中にエラーが発生しました: {e}")

# ==========================================
# タブ2: 最新一覧 (5地点のダッシュボード)
# ==========================================
with tab2:
    st.header("📋 校内WBGT最新状況")
    
    # 最新データの取得
    latest_df = database.get_latest_records()
    
    # 指標の集計と表示
    total_locations = len(config.LOCATIONS)
    measured_count = len(latest_df) if not latest_df.empty else 0
    unmeasured_count = total_locations - measured_count
    
    # 最高WBGT
    if not latest_df.empty:
        highest_row = latest_df.loc[latest_df['wbgt'].idxmax()]
        highest_loc = highest_row['location']
        highest_wbgt_val = highest_row['wbgt']
        
        danger_count = len(latest_df[latest_df['judgment'] == "危険"])
        severe_count = len(latest_df[latest_df['judgment'] == "厳重警戒"])
        last_update = latest_df['observed_at'].max()
    else:
        highest_loc = "データなし"
        highest_wbgt_val = 0.0
        danger_count = 0
        severe_count = 0
        last_update = "未測定"

    # サマリーカード表示
    st.markdown("### 全地点まとめ")
    c1, c2, c3 = st.columns(3)
    c1.metric("測定済み地点数", f"{measured_count} / {total_locations}")
    c2.metric("最高WBGT", f"{highest_wbgt_val:.1f}℃", highest_loc)
    c3.metric("危険 / 厳重警戒", f"{danger_count} / {severe_count} 地点")
    st.caption(f"最終更新時刻: {last_update}")
    
    st.write("---")
    
    # ソートオプション
    sort_by_wbgt = st.checkbox("WBGT値の高い順に並び替える", value=True)
    
    # 表示用テーブルデータの作成
    display_rows = []
    
    for loc in config.LOCATIONS:
        # DBからこの地点の最新レコードを探す
        loc_data = latest_df[latest_df['location'] == loc] if not latest_df.empty else pd.DataFrame()
        
        prev_data = database.get_previous_record(loc)
        
        if not loc_data.empty:
            row = loc_data.iloc[0]
            obs_time = row['observed_at']
            wbgt_val = row['wbgt']
            temp_val = row['temperature']
            hum_val = row['humidity']
            judgment = row['judgment']
            
            # 時間差チェック（1時間以上で警告）
            try:
                time_diff = (datetime.now() - datetime.strptime(obs_time, "%Y-%m-%d %H:%M:%S")).total_seconds() / 3600
                time_status = "⚠️ 情報が古い" if time_diff >= 1.0 else "✅ 最新"
            except:
                time_status = "不明"
            
            # 前回値からの変化計算
            change_str = "-"
            if prev_data and prev_data["observed_at"] != obs_time:
                diff = wbgt_val - prev_data["wbgt"]
                change_str = f"{'+' if diff >= 0 else ''}{diff:.1f}℃"
                
            display_rows.append({
                "地点": loc,
                "観測時刻": obs_time,
                "状態": time_status,
                "WBGT(℃)": wbgt_val,
                "気温(℃)": temp_val,
                "湿度(%)": hum_val,
                "熱中症判定": judgment,
                "前回差": change_str,
                "測定": "測定済み"
            })
        else:
            display_rows.append({
                "地点": loc,
                "観測時刻": "-",
                "状態": "未測定",
                "WBGT(℃)": None,
                "気温(℃)": None,
                "湿度(%)": None,
                "熱中症判定": "未測定",
                "前回差": "-",
                "測定": "未測定"
            })
            
    display_df = pd.DataFrame(display_rows)
    
    if sort_by_wbgt:
        # WBGTの高い順（Noneは最下位）
        display_df = display_df.sort_values(by="WBGT(℃)", ascending=False, na_position='last')
        
    # テーブル表示をカラフルにするカスタムHTML/CSSでの描画
    st.subheader("地点別一覧表")
    for index, row in display_df.iterrows():
        color = wbgt_rules.get_judgment_color(row['熱中症判定'])
        
        with st.container():
            st.markdown(
                f"""
                <div style="border-left: 10px solid {color}; padding: 12px; margin-bottom: 10px; background-color: #f8f9fa; border-radius: 4px; box-shadow: 1px 1px 3px rgba(0,0,0,0.1);">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-size: 1.2rem; font-weight: bold; color: #333;">{row['地点']}</span>
                        <span style="background-color: {color}; color: white; padding: 4px 12px; border-radius: 12px; font-weight: bold;">{row['熱中症判定']}</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; margin-top: 8px; font-size: 0.95rem; color: #555;">
                        <span><b>WBGT:</b> {f"{row['WBGT(℃)']:.1f}℃" if row['WBGT(℃)'] is not None else '未計測'} ({row['前回差']})</span>
                        <span><b>気温:</b> {f"{row['気温(℃)']:.1f}℃" if row['気温(℃)'] is not None else '未計測'}</span>
                        <span><b>湿度:</b> {f"{row['湿度(%)']:.1f}%" if row['湿度(%)'] is not None else '未計測'}</span>
                    </div>
                    <div style="font-size: 0.8rem; color: #888; text-align: right; margin-top: 4px;">
                        観測時刻: {row['観測時刻']} | 状態: {row['状態']}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

# ==========================================
# タブ3: 履歴・グラフ
# ==========================================
with tab3:
    st.header("📊 履歴データ分析")
    
    # 1. 日付選択
    selected_date = st.date_input("表示する日付を選択", datetime.today())
    date_str = selected_date.strftime("%Y-%m-%d")
    
    # データの取得
    day_df = database.get_records_by_date(date_str)
    
    if day_df.empty:
        st.info(f"{date_str} の観測記録はありません。")
    else:
        st.subheader(f"📅 {date_str} の一覧データ")
        st.dataframe(day_df, use_container_width=True)
        
        # CSVエクスポート
        csv = day_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="この日のデータをCSVダウンロード",
            data=csv,
            file_name=f"WBGT_records_{date_str}.csv",
            mime="text/csv"
        )
        
        st.write("---")
        st.subheader("📈 時系列推移グラフ")
        
        # グラフ用の地点選択
        graph_loc = st.selectbox("グラフ表示する地点を選択", config.LOCATIONS, key="graph_loc_select")
        history_df = database.get_location_history(graph_loc, date_str)
        
        if history_df.empty:
            st.warning(f"{graph_loc} の時系列データが存在しません。")
        else:
            # Plotlyでスマホでも見やすいマルチライングラフを描画
            fig = px.line(
                history_df,
                x="observed_at",
                y=["wbgt", "temperature", "humidity"],
                labels={"observed_at": "測定時刻", "value": "数値", "variable": "項目"},
                title=f"{graph_loc} の環境指標推移 ({date_str})",
                markers=True
            )
            fig.update_layout(
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                margin=dict(l=20, r=20, t=60, b=20)
            )
            st.plotly_chart(fig, use_container_width=True)

# ==========================================
# タブ4: Classi投稿用テキスト
# ==========================================
with tab4:
    st.header("💬 連絡連絡用テキスト作成")
    st.write("下のテキストボックスから文章を直接コピーしてClassiへ貼り付けることができます。")
    
    # Classi投稿用のテキスト生成
    latest_all = database.get_latest_records()
    
    post_text = wbgt_rules.generate_classi_post(latest_all, config.LOCATIONS)
    
    st.text_area(
        label="Classi 投稿文 (コピー用)",
        value=post_text,
        height=280
    )
