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
        "days_since_last_active": None,
    }


def calculate_org_summary(df_org_log, df_org_reg, as_of_date=None):
    """สรุปภาพรวมองค์กรภายนอกทั้งหมด: จำนวนบริษัทที่สมัคร, จำนวนคนที่สมัคร, นาทีสะสมรวมที่บันทึกจริง

    รวมนาทีสะสมจากทุกบริษัท (ดูสูตรเต็มใน calculate_company_stats)
    """
    if df_org_reg.empty:
        return {
            "total_companies": 0, "total_registered_people": 0, "total_minutes": 0,
            "last_active_date": None, "days_since_last_active": None,
        }

    as_of_date = as_of_date or pd.Timestamp.now(tz=config.TZ_TH).tz_localize(None)
    reg_by_company = df_org_reg.set_index('บริษัท')['จำนวนคนสมัคร'].to_dict()
    total_minutes = sum(
        calculate_company_stats(df_org_log, company, registered)['total_minutes']
        for company, registered in reg_by_company.items()
    )

    # หา max ตรงจาก log รวมทั้งหมด (ไม่วนลูปต่อบริษัทเหมือน total_minutes ด้านบน) เพราะแค่ต้องการ
    # วันล่าสุดที่ "มีบริษัทไหนก็ได้" ทำ ไม่ต้องแยกรายบริษัท
    last_active_date = df_org_log['วันที่ทำ'].max() if not df_org_log.empty else None
    days_since_last_active = None
    if last_active_date is not None and pd.notna(last_active_date):
        # .normalize() ตัดเวลาออกก่อนลบ (as_of_date มีเวลาปนมาจาก pd.Timestamp.now())
        days_since_last_active = (as_of_date.normalize() - last_active_date.normalize()).days

    return {
        "total_companies": df_org_reg['บริษัท'].nunique(),
        "total_registered_people": int(df_org_reg['จำนวนคนสมัคร'].sum()),
        "total_minutes": total_minutes,
        "last_active_date": last_active_date,
        "days_since_last_active": days_since_last_active,
    }


def _business_days_between(start_date, end_date):
    """นับจำนวนวันทำการ (จันทร์-ศุกร์) รวมทั้งวันเริ่มและวันจบ"""
    if start_date > end_date:
        return 0
    return len(pd.bdate_range(start_date, end_date))


def default_forecast_periods(as_of_date=None):
    """เดือนถัดจากเดือนปัจจุบัน จนถึงเดือนธันวาคมของปีเดียวกัน ใช้เป็นช่วงพยากรณ์เริ่มต้น (ว่างเปล่าถ้าปัจจุบันคือ/เลยธันวาคมแล้ว)"""
    as_of_date = as_of_date or pd.Timestamp.now(tz=config.TZ_TH).tz_localize(None)
    current_period = pd.Period(as_of_date, freq='M')
    year_end = pd.Period(f"{as_of_date.year}-12", freq='M')
    if current_period >= year_end:
        return []
    return list(pd.period_range(current_period + 1, year_end, freq='M'))


def calculate_monthly_actual(df_org_log, company_name, registered_people, as_of_date=None):
    """นาทีสะสมจริงรายเดือนของบริษัท 1 แห่ง ตั้งแต่เดือนแรกที่เริ่มทำจนถึงเดือนปัจจุบัน

    เติม 0 ให้เดือนที่ไม่มีการทำเลยด้วย (ไม่ข้ามแถว) เพื่อให้เห็นครบทุกเดือนในช่วง
    ใช้หลักการเดียวกับ calculate_company_stats: 1 วันที่มีคนส่งฟอร์ม = ทั้งบริษัททำวันนั้น
    """
    company_log = df_org_log[df_org_log['บริษัท'] == company_name]
    if company_log.empty:
        return pd.DataFrame(columns=['บริษัท', 'เดือน', 'วันที่ทำ', 'นาทีสะสม'])

    as_of_date = as_of_date or pd.Timestamp.now(tz=config.TZ_TH).tz_localize(None)
    active_dates = pd.Series(sorted(set(company_log['วันที่ทำ'].dt.date)))
    counts = active_dates.groupby(pd.to_datetime(active_dates).dt.to_period('M')).size()

    first_period = pd.Period(company_log['วันที่ทำ'].min(), freq='M')
    last_period = pd.Period(as_of_date, freq='M')
    if last_period < first_period:
        last_period = first_period
    counts = counts.reindex(pd.period_range(first_period, last_period, freq='M'), fill_value=0)

    monthly = counts.reset_index()
    monthly.columns = ['เดือน', 'วันที่ทำ']
    monthly['บริษัท'] = company_name
    monthly['นาทีสะสม'] = monthly['วันที่ทำ'] * registered_people * config.ORG_MINUTES_PER_PERSON_DAY
    monthly['เดือน'] = monthly['เดือน'].astype(str)
    return monthly[['บริษัท', 'เดือน', 'วันที่ทำ', 'นาทีสะสม']].reset_index(drop=True)


def forecast_monthly(df_org_log, company_name, registered_people, future_periods, as_of_date=None):
    """พยากรณ์นาทีของเดือนที่ยังไม่ถึง (future_periods: list ของ pd.Period freq='M')

    คำนวณ 2 แบบเทียบกัน:
    - พยากรณ์ (run-rate): ใช้อัตราการทำจริงในวันทำการที่ผ่านมา (นับจากวันแรกที่บริษัทเริ่มทำ) คูณจำนวนวันทำการของเดือนนั้น
      สะท้อนพฤติกรรมจริง ใช้เป็นค่าหลักสำหรับกรอกประมาณการ
    - เต็มอัตรา (100%): สมมติทำครบทุกวันทำการในเดือนนั้น (คนสมัคร x วันทำการ x นาที/คน/วัน) เป็นค่าสูงสุดที่เป็นไปได้ ไว้เทียบ
    """
    if not future_periods:
        return pd.DataFrame(columns=['บริษัท', 'เดือน', 'วันทำการ', 'พยากรณ์ (run-rate)', 'เต็มอัตรา (100%)'])

    as_of_date = as_of_date or pd.Timestamp.now(tz=config.TZ_TH).tz_localize(None)
    company_log = df_org_log[df_org_log['บริษัท'] == company_name]

    participation_rate = 0.0
    if not company_log.empty and registered_people > 0:
        active_dates = set(company_log['วันที่ทำ'].dt.date)
        weekday_active_days = sum(1 for d in active_dates if d.weekday() < 5)
        first_active = company_log['วันที่ทำ'].min().date()
        elapsed_bdays = _business_days_between(first_active, as_of_date.date())
        if elapsed_bdays > 0:
            participation_rate = min(weekday_active_days / elapsed_bdays, 1.0)

    rows = []
    for period in future_periods:
        bdays_in_month = _business_days_between(period.start_time.date(), period.end_time.date())
        full_minutes = bdays_in_month * registered_people * config.ORG_MINUTES_PER_PERSON_DAY
        rows.append({
            'บริษัท': company_name,
            'เดือน': str(period),
            'วันทำการ': bdays_in_month,
            'พยากรณ์ (run-rate)': round(full_minutes * participation_rate),
            'เต็มอัตรา (100%)': full_minutes,
        })
    return pd.DataFrame(rows)


def calculate_org_monthly_table(df_org_log, df_org_reg, future_periods, as_of_date=None):
    """ตารางเดียวรวมนาทีสะสมรายเดือนของทุกบริษัท: แถว = บริษัท (+ แถวรวมท้ายตาราง), คอลัมน์ = เดือน (จริงก่อน พยากรณ์ทีหลัง) + คอลัมน์รวม

    เดือนจริงใช้ตัวเลขที่ทำจริง (calculate_monthly_actual) ส่วนเดือนอนาคตใช้ค่าพยากรณ์แบบ run-rate (forecast_monthly)
    เดือน/บริษัทที่ไม่มีข้อมูลใส่ 0 ทั้งหมด ไม่เว้นว่าง
    """
    if df_org_reg.empty:
        return pd.DataFrame()

    reg_by_company = df_org_reg.set_index('บริษัท')['จำนวนคนสมัคร'].to_dict()
    companies = sorted(reg_by_company.keys())

    actual_frames = [
        calculate_monthly_actual(df_org_log, c, reg_by_company[c], as_of_date) for c in companies
    ]
    actual_frames = [f for f in actual_frames if not f.empty]
    actual_long = (
        pd.concat(actual_frames, ignore_index=True)[['บริษัท', 'เดือน', 'นาทีสะสม']]
        if actual_frames else pd.DataFrame(columns=['บริษัท', 'เดือน', 'นาทีสะสม'])
    )

    forecast_frames = [
        forecast_monthly(df_org_log, c, reg_by_company[c], future_periods, as_of_date) for c in companies
    ]
    forecast_frames = [f for f in forecast_frames if not f.empty]
    forecast_long = (
        pd.concat(forecast_frames, ignore_index=True)
        .rename(columns={'พยากรณ์ (run-rate)': 'นาทีสะสม'})[['บริษัท', 'เดือน', 'นาทีสะสม']]
        if forecast_frames else pd.DataFrame(columns=['บริษัท', 'เดือน', 'นาทีสะสม'])
    )

    combined = pd.concat([actual_long, forecast_long], ignore_index=True)
    if combined.empty:
        return pd.DataFrame({'บริษัท': companies})

    pivot = combined.pivot_table(index='บริษัท', columns='เดือน', values='นาทีสะสม', aggfunc='sum', fill_value=0)
    pivot = pivot.reindex(companies, fill_value=0)
    pivot = pivot[sorted(pivot.columns)]
    pivot['รวม'] = pivot.sum(axis=1)

    total_row = pivot.sum(axis=0).to_frame().T
    total_row.index = ['รวม']
    pivot = pd.concat([pivot, total_row])

    pivot.index.name = 'บริษัท'
    pivot = pivot.reset_index()
    for col in pivot.columns[1:]:
        pivot[col] = pivot[col].astype(int)
    return pivot


def calculate_company_stats(df_org, company_name, registered_people=0, as_of_date=None):
    """คำนวณสถิติของบริษัท 1 แห่ง: ยอดสมัคร/วันที่ปฏิบัติ/นาทีสะสม และความต่อเนื่อง (streak)

    นาทีสะสม: คนที่ส่งฟอร์มมีหน้าที่รายงานแทนทั้งบริษัท ไม่ใช่รายงานแค่ตัวเอง ดังนั้น 1 วันที่มีคนส่งฟอร์ม (ไม่ว่ากี่คน)
    ถือว่า "ทั้งบริษัท" ทำวันนั้น = จำนวนคนที่สมัคร x ORG_MINUTES_PER_PERSON_DAY นาที แล้วรวมทุกวันที่ทำ

    ไล่ทีละวันตามลำดับเวลา: วันทำการ (จันทร์-ศุกร์) ต้องทำถึงจะนับต่อเนื่อง ขาดวันใดวันหนึ่ง
    streak ขาดทันที ส่วนเสาร์-อาทิตย์ข้ามได้โดยไม่กระทบ streak แต่ถ้าทำก็ยังนับรวมเป็นวันต่อเนื่อง
    """
    as_of_date = as_of_date or pd.Timestamp.now(tz=config.TZ_TH).tz_localize(None)
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
        # .normalize() ตัดเวลาออกก่อนลบ (as_of_date มีเวลาปนมาจาก pd.Timestamp.now())
        "days_since_last_active": (as_of_date.normalize() - max_date.normalize()).days,
    }
