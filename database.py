# -*- coding: utf-8 -*-
"""
Created on Thu Jul 16 15:14:34 2026

@author: yurie
"""

# database.py
import sqlite3
import pandas as pd
import os
from datetime import datetime
import config

def get_connection():
    """データベース接続を取得します"""
    os.makedirs(config.DB_DIR, exist_ok=True)
    os.makedirs(config.IMAGE_SAVE_DIR, exist_ok=True)
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """テーブルを作成します"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS wbgt_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            location TEXT NOT NULL,
            observed_at TEXT NOT NULL,
            wbgt REAL NOT NULL,
            temperature REAL NOT NULL,
            humidity REAL NOT NULL,
            judgment TEXT NOT NULL,
            image_filename TEXT,
            ocr_wbgt TEXT,
            ocr_temperature TEXT,
            ocr_humidity TEXT,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def insert_record(location, observed_at, wbgt, temp, humidity, judgment, image_filename, ocr_wbgt, ocr_temp, ocr_humidity):
    """観測データを登録します"""
    conn = get_connection()
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 重複登録防止チェック (同じ地点、同じ観測時間)
    cursor.execute(
        "SELECT id FROM wbgt_records WHERE location = ? AND observed_at = ?",
        (location, observed_at)
    )
    if cursor.fetchone():
        conn.close()
        raise ValueError(f"【エラー】{location} の {observed_at} のデータは既に登録されています。")

    cursor.execute("""
        INSERT INTO wbgt_records (
            location, observed_at, wbgt, temperature, humidity, judgment, 
            image_filename, ocr_wbgt, ocr_temperature, ocr_humidity, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (location, observed_at, wbgt, temp, humidity, judgment, image_filename, ocr_wbgt, ocr_temp, ocr_humidity, now_str))
    
    conn.commit()
    conn.close()

def get_latest_records():
    """全地点の最新観測データを取得します"""
    conn = get_connection()
    # 各地点の最新レコードを抽出するクエリ
    query = """
        SELECT r1.* FROM wbgt_records r1
        INNER JOIN (
            SELECT location, MAX(observed_at) as max_time
            FROM wbgt_records
            GROUP BY location
        ) r2 ON r1.location = r2.location AND r1.observed_at = r2.max_time
        ORDER BY r1.observed_at DESC
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def get_previous_record(location):
    """特定地点の1つ前のデータを取得します（時間差比較用）"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM wbgt_records 
        WHERE location = ? 
        ORDER BY observed_at DESC LIMIT 1
    """, (location,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None

def get_records_by_date(date_str):
    """指定された日付（YYYY-MM-DD）のデータを取得します"""
    conn = get_connection()
    # SQLiteのdate関数を使って日付部分でフィルタ
    query = """
        SELECT id, location, observed_at, wbgt, temperature, humidity, judgment, created_at
        FROM wbgt_records
        WHERE strftime('%Y-%m-%d', observed_at) = ?
        ORDER BY observed_at DESC
    """
    df = pd.read_sql_query(query, conn, params=(date_str,))
    conn.close()
    return df

def get_location_history(location, date_str):
    """特定地点の指定日の時系列データを取得します"""
    conn = get_connection()
    query = """
        SELECT observed_at, wbgt, temperature, humidity
        FROM wbgt_records
        WHERE location = ? AND strftime('%Y-%m-%d', observed_at) = ?
        ORDER BY observed_at ASC
    """
    df = pd.read_sql_query(query, conn, params=(location, date_str))
    conn.close()
    return df