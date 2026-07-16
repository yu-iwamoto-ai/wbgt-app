# -*- coding: utf-8 -*-
"""
Created on Thu Jul 16 15:14:33 2026

@author: yurie
"""

# config.py
import os

# アプリケーション基本設定
APP_TITLE = "学校熱中症対策 WBGT観測システム"
DB_DIR = "data"
DB_PATH = os.path.join(DB_DIR, "wbgt_data.db")
IMAGE_SAVE_DIR = os.path.join(DB_DIR, "images")

# 観測地点リスト（追加・変更はここを編集するだけです）
LOCATIONS = [
    "南館前",
    "体育館",
    "講堂前",
    "職員室前",
    "中庭"
]

# 画像保存のセキュリティ設定
SAVE_ORIGINAL_IMAGE = False  # Falseの場合、プライバシー保護のためトリミング後の液晶部分のみ保存
REMOVE_EXIF_DATA = True       # 保存・処理前にEXIF（位置情報含む）を完全に削除する

# AD-5695DLB の液晶領域切り抜き用の相対座標設定 (0.0 〜 1.0)
# 液晶画面全体（ユーザーが撮影した切り抜き対象）を基準とする
# 液晶の各セグメントの大まかな位置比率
ROI_CONFIG = {
    # 上段中央：WBGT (y: 10%~45%, x: 20%~80%)
    "wbgt": {
        "ymin": 0.10, "ymax": 0.45,
        "xmin": 0.20, "xmax": 0.80
    },
    # 左下：気温 TA (y: 55%~90%, x: 5%~50%)
    "ta": {
        "ymin": 0.55, "ymax": 0.90,
        "xmin": 0.05, "xmax": 0.50
    },
    # 右下：湿度 RH (y: 55%~90%, x: 50%~95%)
    "rh": {
        "ymin": 0.55, "ymax": 0.90,
        "xmin": 0.50, "xmax": 0.95
    }
}