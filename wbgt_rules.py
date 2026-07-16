# -*- coding: utf-8 -*-
"""
Created on Thu Jul 16 15:18:33 2026

@author: yurie
"""

# wbgt_rules.py
from datetime import datetime

def judge_wbgt(wbgt):
    """
    WBGT値から日本スポーツ協会/環境省の指針に基づく判定を行います
    """
    if wbgt < 21.0:
        return "ほぼ安全"
    elif 21.0 <= wbgt < 25.0:
        return "注意"
    elif 25.0 <= wbgt < 28.0:
        return "警戒"
    elif 28.0 <= wbgt < 31.0:
        return "厳重警戒"
    else:
        return "危険"

def get_judgment_color(judgment):
    """
    判定に応じたカラーコードを返します（UIの視覚的強調用）
    """
    colors = {
        "ほぼ安全": "#28a745", # 緑
        "注意": "#ffc107",     # 黄色
        "警戒": "#fd7e14",     # オレンジ
        "厳重警戒": "#e83e8c", # ピンク
        "危険": "#dc3545"      # 赤
    }
    return colors.get(judgment, "#6c757d")

def generate_classi_post(latest_df, locations_list):
    """
    最新の一覧データからClassiへ貼り付ける用のテキスト文章を生成します
    """
    now_str = datetime.now().strftime("%H:%M")
    
    lines = []
    lines.append(f"【校内WBGT情報 {now_str}更新】\n")
    
    highest_wbgt = -999.0
    highest_loc = "なし"
    unmeasured_locs = []
    
    # 全地点を走査
    for loc in locations_list:
        # 最新データ内にその地点があるか探す
        loc_data = latest_df[latest_df['location'] == loc]
        if not loc_data.empty:
            row = loc_data.iloc[0]
            wbgt_val = row['wbgt']
            judgment = row['judgment']
            lines.append(f"{loc} {wbgt_val:.1f}℃ {judgment}")
            
            if wbgt_val > highest_wbgt:
                highest_wbgt = wbgt_val
                highest_loc = loc
        else:
            unmeasured_locs.append(loc)
            
    lines.append("") # 空行
    
    if highest_wbgt > -900:
        lines.append(f"最高値：{highest_loc} {highest_wbgt:.1f}℃")
    else:
        lines.append("最高値：なし")
        
    if unmeasured_locs:
        lines.append(f"未測定地点：{', '.join(unmeasured_locs)}")
    else:
        lines.append("未測定地点：なし")
        
    return "\n".join(lines)