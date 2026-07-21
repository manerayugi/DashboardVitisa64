"""คำนวณสถิติการปฏิบัติสมาธิรายบุคคลและภาพรวมโครงการ

หัวใจของไฟล์นี้คือ calculate_user_stats() ซึ่งหาว่าผู้ปฏิบัติแต่ละคน:
1. ทำต่อเนื่องกันสูงสุดกี่วัน (Max Streak)
2. เคยมีช่วง 30 วันติดต่อกันที่สะสมนาทีครบเกณฑ์เกียรติบัตรหรือยัง (Certification Window)
"""
import pandas as pd

import config


def calculate_admin_stats(df_log):
    """สรุปภาพรวมแบบง่ายสำหรับ Admin Dashboard (จำนวนคนที่เริ่มปฏิบัติ + นาทีสะสมรวมทั้งโครงการ)"""
    if df_log.empty:
        return {"total_users": 0, "total_minutes": 0}

    return {
        "total_users": df_log['เลือกชื่อผู้ปฏิบัติ'].nunique(),
        "total_minutes": int(df_log['รวมของวันนั้น'].sum() * 5),
    }


def _empty_user_stats(user_log, total_minutes=0, total_days=0):
    """ค่าเริ่มต้นสำหรับผู้ใช้ที่ยังไม่มีข้อมูลการปฏิบัติ (หรือ log ว่างเปล่า)"""
    return {
        "total_minutes": total_minutes, "total_days": total_days,
        "max_streak_days": 0, "minutes_in_max_streak": 0,
        "max_streak_period": "-",
        "is_certified": False, "cert_window_minutes": 0,
        "cert_window_start": "-", "cert_window_end": "-",
        "first_certified_date": None,
        "log_data": user_log
    }


def _find_max_streak(daily_full):
    """ไล่ทีละวันตามลำดับเวลาเพื่อหาช่วงที่ทำต่อเนื่องกันยาวที่สุด (Max Streak)

    เมื่อมีหลายช่วงที่ยาวเท่ากัน จะเลือกช่วงที่สะสมนาทีได้มากกว่า (เผื่อกรณีทำมากกว่า 1 รอบ/วัน)
    คืนค่า (จำนวนวันต่อเนื่องสูงสุด, นาทีรวมในช่วงนั้น, วันเริ่ม, วันสิ้นสุด)
    """
    current_streak = current_streak_mins = 0
    current_start = None
    max_streak = max_streak_mins = 0
    max_start = max_end = None

    for date, sessions in daily_full.items():
        if sessions > 0:
            if current_streak == 0:
                current_start = date
            current_streak += 1
            current_streak_mins += (sessions * 5)
            continue

        # วันนี้ไม่ได้ทำ -> streak ปัจจุบันขาดตอน เช็คว่าเป็นสถิติสูงสุดใหม่หรือไม่ก่อนรีเซ็ต
        if current_streak > max_streak or (current_streak == max_streak and current_streak_mins > max_streak_mins):
            if current_streak > 0:
                max_streak, max_streak_mins = current_streak, current_streak_mins
                max_start, max_end = current_start, date - pd.Timedelta(days=1)
        current_streak = current_streak_mins = 0
        current_start = None

    # เช็ค streak สุดท้ายที่ยังไม่ขาดตอน ณ วันข้อมูลล่าสุด
    if current_streak > max_streak or (current_streak == max_streak and current_streak_mins > max_streak_mins):
        if current_streak > 0:
            max_streak, max_streak_mins = current_streak, current_streak_mins
            max_start, max_end = current_start, daily_full.index[-1]

    return max_streak, max_streak_mins, max_start, max_end


def _find_cert_window(daily_full, min_date, max_date):
    """หาช่วง 30 วัน (rolling window) ที่ทำต่อเนื่องครบและสะสมนาทีได้มากที่สุด

    เกณฑ์ผ่าน: ต้องมีช่วง 30 วันติดต่อกันที่ทำทุกวัน (ไม่ขาด) และนาทีรวมในช่วงนั้น >= 360
    ถ้ามีหลายช่วงที่นาทีเท่ากัน จะเลือกช่วงที่จบเร็วที่สุด (เกิดขึ้นก่อน)
    คืนค่า (is_certified, นาทีในช่วงที่ดีที่สุด, วันเริ่ม, วันสิ้นสุด, วันที่ผ่านเกณฑ์ครั้งแรก)
    """
    if len(daily_full) < config.CERT_TARGET_STREAK:
        # ประวัติสั้นกว่า 30 วัน: ยังตัดสินไม่ได้ว่าผ่านเกณฑ์ แต่โชว์นาทีสะสมทั้งหมดเป็นความคืบหน้า
        if daily_full.sum() > 0:
            cert_minutes = int(daily_full.sum() * 5)
            return False, cert_minutes, min_date.strftime("%d/%m/%Y"), max_date.strftime("%d/%m/%Y"), None
        return False, 0, "-", "-", None

    active_days_rolling = (daily_full > 0).rolling(window=config.CERT_TARGET_STREAK).sum()
    minutes_rolling = (daily_full * 5).rolling(window=config.CERT_TARGET_STREAK).sum()
    perfect_streaks = (active_days_rolling == config.CERT_TARGET_STREAK)

    # เลือก pool ของช่วงที่จะพิจารณา: ช่วงที่ทำครบ 30 วันเป๊ะ ถ้ามี, ไม่งั้นดูช่วงที่ดีที่สุดเท่าที่มี (เพื่อโชว์ progress)
    candidate_minutes = minutes_rolling[perfect_streaks] if perfect_streaks.any() else minutes_rolling
    max_val = candidate_minutes.max()

    if pd.isna(max_val) or max_val <= 0:
        return False, 0, "-", "-", None

    # ใช้ .index[0] เพื่อดึงกรอบเวลาแรกสุดที่ทำคะแนนได้เท่ากับ max_val
    best_end_date = candidate_minutes[candidate_minutes == max_val].index[0]
    best_start_date = best_end_date - pd.Timedelta(days=config.CERT_TARGET_STREAK - 1)
    cert_minutes = int(max_val)
    is_certified = perfect_streaks.any() and cert_minutes >= config.CERT_TARGET_MINUTES_IN_30D

    # วันที่ผ่านเกณฑ์ครั้งแรก: วันแรกสุดที่ต่อเนื่องครบ 30 วัน "และ" นาทีสะสมครบ 360 พร้อมกัน
    # ต่างจาก best_end_date ด้านบนซึ่งเป็นช่วงที่ "นาทีสะสมเยอะสุด" ซึ่งอาจเกิดขึ้นทีหลังกว่าครั้งแรกที่ผ่านเกณฑ์จริงๆ
    first_certified_date = None
    if is_certified:
        qualified = perfect_streaks & (minutes_rolling >= config.CERT_TARGET_MINUTES_IN_30D)
        first_certified_date = qualified[qualified].index.min()

    return is_certified, cert_minutes, best_start_date.strftime("%d/%m/%Y"), best_end_date.strftime("%d/%m/%Y"), first_certified_date


def calculate_monthly_actual(df_log, user_name, as_of_date=None):
    """นาทีสะสมจริงรายเดือนของผู้ปฏิบัติ 1 คน ตั้งแต่เดือนแรกที่เริ่มทำจนถึงเดือนปัจจุบัน

    เติม 0 ให้เดือนที่ไม่ได้ทำเลยด้วย (ไม่ข้ามแถว) เพื่อให้เห็นครบทุกเดือนในช่วง
    """
    user_log = df_log[df_log['เลือกชื่อผู้ปฏิบัติ'] == user_name]
    if user_log.empty:
        return pd.DataFrame(columns=['ชื่อ-นามสกุล', 'เดือน', 'นาทีสะสม'])

    as_of_date = as_of_date or pd.Timestamp.now(tz=config.TZ_TH).tz_localize(None)
    monthly_minutes = (user_log.groupby(user_log['วันที่ปฏิบัติ'].dt.to_period('M'))['รวมของวันนั้น'].sum() * 5)

    first_period = pd.Period(user_log['วันที่ปฏิบัติ'].min(), freq='M')
    last_period = pd.Period(as_of_date, freq='M')
    if last_period < first_period:
        last_period = first_period
    monthly_minutes = monthly_minutes.reindex(pd.period_range(first_period, last_period, freq='M'), fill_value=0)

    monthly = monthly_minutes.reset_index()
    monthly.columns = ['เดือน', 'นาทีสะสม']
    monthly['ชื่อ-นามสกุล'] = user_name
    monthly['นาทีสะสม'] = monthly['นาทีสะสม'].astype(int)
    monthly['เดือน'] = monthly['เดือน'].astype(str)
    return monthly[['ชื่อ-นามสกุล', 'เดือน', 'นาทีสะสม']].reset_index(drop=True)


def calculate_users_monthly_table(df_log, all_users, as_of_date=None):
    """ตาราง wide นาทีสะสมรายเดือนของทุกคน: แถว = ชื่อ-นามสกุล, คอลัมน์ = เดือน

    ใช้ต่อเข้ากับตารางสรุปรายบุคคลของ Admin คนที่ไม่มีข้อมูลในเดือนนั้น (ยังไม่เริ่ม/ไม่ได้ทำ) แสดงเป็น 0 ไม่เว้นว่าง
    """
    names = sorted(u for u in all_users if str(u).strip())
    if df_log.empty or not names:
        return pd.DataFrame({'ชื่อ-นามสกุล': names})

    frames = [calculate_monthly_actual(df_log, name, as_of_date) for name in names]
    frames = [f for f in frames if not f.empty]
    if not frames:
        return pd.DataFrame({'ชื่อ-นามสกุล': names})

    combined = pd.concat(frames, ignore_index=True)
    pivot = combined.pivot_table(index='ชื่อ-นามสกุล', columns='เดือน', values='นาทีสะสม', aggfunc='sum', fill_value=0)
    pivot = pivot.reindex(names, fill_value=0)
    pivot = pivot[sorted(pivot.columns)]
    pivot.index.name = 'ชื่อ-นามสกุล'
    pivot = pivot.reset_index()
    for col in pivot.columns[1:]:
        pivot[col] = pivot[col].astype(int)
    return pivot


def calculate_user_stats(df_log, user_name):
    """คำนวณสถิติของผู้ปฏิบัติ 1 คน ตามเกณฑ์เกียรติบัตร: ต่อเนื่อง 30 วัน + นาทีสะสม >= 360 ในช่วงนั้น"""
    user_log = df_log[df_log['เลือกชื่อผู้ปฏิบัติ'] == user_name].copy()

    if user_log.empty:
        return _empty_user_stats(user_log)

    user_log = user_log.sort_values(by='วันที่ปฏิบัติ')
    total_minutes = int(user_log['รวมของวันนั้น'].sum() * 5)
    total_days = len(user_log['วันที่ปฏิบัติ'].dt.date.unique())

    # รวมยอดต่อวัน (เผื่อกรณีมีหลายแถวซ้ำวันเดียวกัน) แล้ว reindex ให้มีทุกวันในช่วง
    # (รวมวันที่ไม่ได้ทำ = 0) เพื่อให้หา Max Streak และ rolling window ได้ถูกต้อง
    daily_series = user_log.groupby(user_log['วันที่ปฏิบัติ'].dt.date)['รวมของวันนั้น'].sum()
    daily_series.index = pd.to_datetime(daily_series.index)

    if daily_series.empty:
        return _empty_user_stats(user_log, total_minutes, total_days)

    min_date, max_date = daily_series.index.min(), daily_series.index.max()
    daily_full = daily_series.reindex(pd.date_range(start=min_date, end=max_date), fill_value=0)

    max_streak, max_streak_mins, max_start, max_end = _find_max_streak(daily_full)
    if max_streak > 0:
        start_str, end_str = max_start.strftime("%d/%m/%Y"), max_end.strftime("%d/%m/%Y")
        max_streak_period = f"{start_str} - {end_str}" if max_streak > 1 else start_str
    else:
        max_streak_period = "-"

    is_certified, cert_window_minutes, cert_window_start, cert_window_end, first_certified_date = _find_cert_window(
        daily_full, min_date, max_date
    )

    return {
        "total_minutes": total_minutes,
        "total_days": total_days,
        "max_streak_days": max_streak,
        "minutes_in_max_streak": max_streak_mins,
        "max_streak_period": max_streak_period,
        "is_certified": is_certified,
        "cert_window_minutes": cert_window_minutes,
        "cert_window_start": cert_window_start,
        "cert_window_end": cert_window_end,
        "first_certified_date": first_certified_date,
        "log_data": user_log
    }
