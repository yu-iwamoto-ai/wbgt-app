# -*- coding: utf-8 -*-
"""
Created on Thu Jul 16 15:14:36 2026

@author: yurie
"""

# ocr_reader.py
import cv2
import re
import numpy as np

# EasyOCRのインポートチェック
try:
    import easyocr
    # 英語(数字含む)のリーダーを初期化 (GPUがあれば自動使用)
    reader = easyocr.Reader(['en'], gpu=False) 
    EASY_OCR_AVAILABLE = True
except ImportError:
    EASY_OCR_AVAILABLE = False

def clean_ocr_text(text):
    """OCR結果から数字、マイナス、ドット以外の文字を排除し、実数に整形します"""
    # 7セグ特有の誤読補正
    text = text.replace('o', '0').replace('O', '0')
    text = text.replace('I', '1').replace('i', '1').replace('|', '1')
    text = text.replace('S', '5').replace('s', '5')
    text = text.replace('B', '8')
    text = text.replace(',', '.') # カンマはドットに置換
    
    # 数字、ドット、マイナスのみ抽出
    matched = re.findall(r'[-+]?\d*\.\d+|\d+', text)
    if matched:
        return matched[0]
    return ""

def read_numeric_value(cv_processed_img):
    """画像から数値を読み取ります"""
    if not EASY_OCR_AVAILABLE:
        return None, "EasyOCR 未インストール"

    try:
        # EasyOCRはRGB画像を想定しているため変換
        # processed_imgが単一チャネル（グレースケール/二値化後）の場合はRGBに戻す
        if len(cv_processed_img.shape) == 2:
            color_img = cv2.cvtColor(cv_processed_img, cv2.COLOR_GRAY2RGB)
        else:
            color_img = cv2.cvtColor(cv_processed_img, cv2.COLOR_BGR2RGB)
            
        # OCR実行
        results = reader.readtext(color_img, allowlist='0123456789.-')
        
        if not results:
            return None, "数値が検出できませんでした"
            
        # 最も信頼度の高い、または中央に位置するテキストを採用
        best_text = results[0][1]
        cleaned = clean_ocr_text(best_text)
        
        if cleaned:
            return float(cleaned), f"成功 ({best_text})"
        else:
            return None, f"不適合文字列: {best_text}"
            
    except Exception as e:
        return None, f"解析エラー: {str(e)}"