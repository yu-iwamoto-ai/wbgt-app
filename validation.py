# -*- coding: utf-8 -*-
"""
Created on Thu Jul 16 15:17:26 2026

@author: yurie
"""

# validation.py
from datetime import datetime
import database

def validate_input(wbgt_val, temp_val, humidity_val):
    """
    入力された数値が現実的な範囲内にあるか検証します。
    エラーがある場合は、エラーメッセージのリストを返します。
    """
    errors = []
    
    # WBGTチェック
    if wbgt_val is None:
        errors.append("WBGTが入力されていません。")
    elif not (0.0 <= wbgt_val <= 50.0):
        errors.append("WBGTは 0℃ 〜 50℃ の範囲で入力してください。")
        
    # 気温チェック
    if temp_val is None:
        errors.append("気温が入力されていません。")
    elif not (-10.0 <= temp_val <= 60.0):
        errors.append("気温は -10℃ 〜 60℃ の範囲で入力してください。")
        
    # 湿度チェック
    if humidity_val is None:
        errors.append("湿度が入力されていません。")
    elif not (0.0 <= humidity_val <= 100.0):
        errors.append("湿度は 0% 〜 100% の範囲で入力してください。")
        
    return errors

def check_sudden_change(location, new_wbgt, new_temp, new_time_str):
    """
    同じ地点の30分以内の直前値と比較し、
    WBGTまたは気温が10℃以上急変している場合に警告を返します。
    """
    prev = database.get_previous_record(location)
    if not prev:
        return None # 前回の記録がない場合は警告なし
        
    try:
        fmt = "%Y-%m-%d %H:%M:%S"
        # 入力タイムスタンプの長さを揃える (分単位: %Y-%m-%d %H:%M)
        new_time = datetime.strptime(new_time_str, fmt if len(new_time_str) == 19 else "%Y-%m-%dT%H:%M")
        prev_time = datetime.strptime(prev["observed_at"], fmt)
        
        # 時間差を分で算出
        time_diff_mins = abs((new_time - prev_time).total_seconds()) / 60.0
        
        if time_diff_mins <= 30.0:
            wbgt_diff = abs(new_wbgt - prev["wbgt"])
            temp_diff = abs(new_temp - prev["temperature"])
            
            if wbgt_diff >= 10.0 or temp_diff >= 10.0:
                return (
                    f"【注意】直前の測定（{prev['observed_at']}）から30分以内に "
                    f"WBGTまたは気温が10℃以上急変化しています。\n"
                    f"前回値：WBGT {prev['wbgt']}℃ / 気温 {prev['temperature']}℃\n"
                    f"入力値：WBGT {new_wbgt}℃ / 気温 {new_temp}℃\n"
                    f"写真と数値に間違いがないか、再確認してください。"
                )
    except Exception as e:
        # パースエラー等の場合は警告スキップ
        return None
        
    return None