"""คำนวณความต่อเนื่อง (Streak) รายบริษัทของฟอร์มบันทึกผลองค์กรภายนอก

หัวใจของไฟล์นี้คือ calculate_company_stats() ซึ่งนับ "วันทำการต่อเนื่อง" ที่บริษัทมีคนส่งฟอร์ม
อย่างน้อย 1 ครั้ง เกณฑ์ผ่านคือสะสมให้ครบ config.ORG_STREAK_TARGET วัน โดยวันเสาร์-อาทิตย์ที่ไม่ได้ทำ
จะไม่ทำให้ streak ขาด แต่ถ้าทำก็นับรวมเป็นวันต่อเนื่องด้วย (เช่น ทำจันทร์-เสาร์ นับเป็น 6 วัน ไม่ใช่ 5)
"""
import pandas as pd

import config


def _empty_company_stats():
    return {
        "total_days_done": 0,
        "max_streak_days": 0,
        "max_streak_period": "-",
        "is_qualified": False,
        "first_qualified_date": None,
        "last_active_date": None,
    }


def calculate_company_stats(df_org, company_name):
    """คำนวณสถิติความต่อเนื่องของบริษัท 1 แห่ง

    ไล่ทีละวันตามลำดับเวลา: วันทำการ (จันทร์-ศุกร์) ต้องทำถึงจะนับต่อเนื่อง ขาดวันใดวันหนึ่ง
    streak ขาดทันที ส่วนเสาร์-อาทิตย์ข้ามได้โดยไม่กระทบ streak แต่ถ้าทำก็ยังนับรวมเป็นวันต่อเนื่อง
    """
    company_log = df_org[df_org['บริษัท'] == company_name]
    if company_log.empty:
        return _empty_company_stats()

    active_dates = set(company_log['วันที่ทำ'].dt.date)
    min_date, max_date = company_log['วันที่ทำ'].min(), company_log['วันที่ทำ'].max()
    full_range = pd.date_range(start=min_date, end=max_date)

    streak = 0
    streak_start = None
    max_streak, max_start, max_end = 0, None, None
    first_qualified_date = None

    for date in full_range:
        is_active = date.date() in active_dates
        is_weekend = date.weekday() >= 5  # 5 = เสาร์, 6 = อาทิตย์

        if is_active:
            if streak == 0:
                streak_start = date
            streak += 1
            if streak > max_streak:
                max_streak, max_start, max_end = streak, streak_start, date
            if streak >= config.ORG_STREAK_TARGET and first_qualified_date is None:
                first_qualified_date = date
        elif not is_weekend:
            # วันทำการที่ขาด -> streak ขาดทันที
            streak = 0
            streak_start = None
        # เสาร์-อาทิตย์ที่ไม่ได้ทำ: ไม่ทำอะไร (streak คงเดิม ไม่ขาดไม่เพิ่ม)

    max_streak_period = "-"
    if max_streak > 0:
        start_str, end_str = max_start.strftime("%d/%m/%Y"), max_end.strftime("%d/%m/%Y")
        max_streak_period = f"{start_str} - {end_str}" if max_streak > 1 else start_str

    return {
        "total_days_done": len(active_dates),
        "max_streak_days": max_streak,
        "max_streak_period": max_streak_period,
        "is_qualified": max_streak >= config.ORG_STREAK_TARGET,
        "first_qualified_date": first_qualified_date,
        "last_active_date": max_date,
    }
