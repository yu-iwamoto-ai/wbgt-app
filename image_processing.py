# -*- coding: utf-8 -*-
"""
Created on Thu Jul 16 15:14:34 2026

@author: yurie
"""

# image_processing.py
import cv2
import numpy as np
from PIL import Image, ImageOps
import io
import config

def preprocess_uploaded_image(uploaded_file):
    """
    アップロードされた画像をPILで読み込み、EXIFに基づいて向きを自動補正し、
    EXIFメタデータを破棄した新しい画像オブジェクトを返します。
    """
    img = Image.open(uploaded_file)
    
    # EXIFに基づく回転自動補正
    try:
        img = ImageOps.exif_transpose(img)
    except Exception:
        # EXIF解析エラー時はそのまま通す
        pass
        
    # EXIFデータを引き継がないようにRGBに変換して新規作成
    clean_img = Image.new("RGB", img.size)
    clean_img.paste(img)
    return clean_img

def crop_roi(cv_img, roi_key):
    """configで定義された比率に基づいて、画像から指定領域を切り抜きます"""
    h, w = cv_img.shape[:2]
    cfg = config.ROI_CONFIG[roi_key]
    
    ymin, ymax = int(cfg["ymin"] * h), int(cfg["ymax"] * h)
    xmin, xmax = int(cfg["xmin"] * w), int(cfg["xmax"] * w)
    
    return cv_img[ymin:ymax, xmin:xmax]

def apply_ocr_preprocessing(cv_crop):
    """
    7セグメント液晶文字をOCRしやすくするための画像処理
    """
    # 1. グレースケール化
    gray = cv2.cvtColor(cv_crop, cv2.COLOR_BGR2GRAY)
    
    # 2. リサイズ (解像度が低すぎる場合は拡大)
    h, w = gray.shape[:2]
    if w < 200:
        scale = 300 / w
        gray = cv2.resize(gray, (0, 0), fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        
    # 3. コントラストの均一化 (CLAHE)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    
    # 4. 二値化 (適応的しきい値処理、黒背景に白文字または白背景に黒文字)
    # 液晶表示は文字が暗く背景が明るいことが多いため、大津の二値化を試す
    _, threshed = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    
    # 5. ノイズ除去
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    cleaned = cv2.morphologyEx(threshed, cv2.MORPH_CLOSE, kernel)
    
    return cleaned