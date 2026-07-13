"""คำนวณความต่อเนื่อง (Streak) รายบริษัทของฟอร์มบันทึกผลองค์กรภายนอก

หัวใจของไฟล์นี้คือ calculate_company_stats() ซึ่งนับ "วันทำการต่อเนื่อง" ที่บริษัทมีคนส่งฟอร์ม
อย่างน้อย 1 ครั้ง เกณฑ์ผ่านคือสะสมให้ครบ config.ORG_STREAK_TARGET วัน โดยวันเสาร์-อาทิตย์ที่ไม่ได้ทำ
จะไม่ทำให้ streak ขาด แต่ถ้าทำก็นับรวมเป็นวันต่อเนื่องด้วย (เช่น ทำจันทร์-เสาร์ นับเป็น 6 วัน ไม่ใช่ 5)
"""
import pandas as pd

import config


def _empty_company_stats(registered_people=0):
    return {
        "registered_people": registered_people,
        "total_minutes": 0,
        "total_days_done": 0,
        "max_streak_days": 0,
        "max_streak_period": "-",
        "is_qualified": False,
        "first_qualified_date": None,
        "last_active_date": None,
    }


def calculate_org_summary(df_org_log, df_org_reg):
    """สรุปภาพรวมองค์กรภายนอกทั้งหมด: จำนวนบริษัทที่สมัคร, จำนวนคนที่สมัคร, นาทีสะสมรวมที่บันทึกจริง

    รวมนาทีสะสมจากทุกบริษัท (ดูสูตรเต็มใน calculate_company_stats)
    """
    if df_org_reg.empty:
        return {"total_companies": 0, "total_registered_people": 0, "total_minutes": 0}

    reg_by_company = df_org_reg.set_index('บริษัท')['จำนวนคนสมัคร'].to_dict()
    total_minutes = sum(
        calculate_company_stats(df_org_log, company, registered)['total_minutes']
        for company, registered in reg_by_company.items()
    )

    return {
        "total_companies": df_org_reg['บริษัท'].nunique(),
        "total_registered_people": int(df_org_reg['จำนวนคนสมัคร'].sum()),
        "total_minutes": total_minutes,
    }


def calculate_company_stats(df_org, company_name, registered_people=0):
    """คำนวณสถิติของบริษัท 1 แห่ง: ยอดสมัคร/วันที่ปฏิบัติ/นาทีสะสม และความต่อเนื่อง (streak)

    นาทีสะสม: คนที่ส่งฟอร์มมีหน้าที่รายงานแทนทั้งบริษัท ไม่ใช่รายงานแค่ตัวเอง ดังนั้น 1 วันที่มีคนส่งฟอร์ม (ไม่ว่ากี่คน)
    ถือว่า "ทั้งบริษัท" ทำวันนั้น = จำนวนคนที่สมัคร x ORG_MINUTES_PER_PERSON_DAY นาที แล้วรวมทุกวันที่ทำ

    ไล่ทีละวันตามลำดับเวลา: วันทำการ (จันทร์-ศุกร์) ต้องทำถึงจะนับต่อเนื่อง ขาดวันใดวันหนึ่ง
    streak ขาดทันที ส่วนเสาร์-อาทิตย์ข้ามได้โดยไม่กระทบ streak แต่ถ้าทำก็ยังนับรวมเป็นวันต่อเนื่อง
    """
    company_log = df_org[df_org['บริษัท'] == company_name]
    if company_log.empty:
        return _empty_company_stats(registered_people)

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
        "registered_people": registered_people,
        "total_minutes": len(active_dates) * registered_people * config.ORG_MINUTES_PER_PERSON_DAY,
        "total_days_done": len(active_dates),
        "max_streak_days": max_streak,
        "max_streak_period": max_streak_period,
        "is_qualified": max_streak >= config.ORG_STREAK_TARGET,
        "first_qualified_date": first_qualified_date,
        "last_active_date": max_date,
    }
