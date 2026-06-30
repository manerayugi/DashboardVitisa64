import pandas as pd
import streamlit as st
import datetime

@st.cache_data(ttl=600)
def load_data():
    try:
        reg_url = st.secrets["sheets"]["reg_url"]
        log_url = st.secrets["sheets"]["log_url"]
        
        df_reg = pd.read_csv(reg_url)
        df_log = pd.read_csv(log_url)
        
        if 'เบอร์ติดต่อ' in df_reg.columns:
            df_reg['เบอร์ติดต่อ'] = df_reg['เบอร์ติดต่อ'].astype(str).str.replace(r'\.0$', '', regex=True)
            df_reg['เบอร์ติดต่อ'] = df_reg['เบอร์ติดต่อ'].str.replace(r'\D', '', regex=True).str.zfill(10)
            
        if 'ชื่อ_นามสกุล' in df_reg.columns:
            df_reg['ชื่อ_นามสกุล'] = df_reg['ชื่อ_นามสกุล'].astype(str).str.replace(r'\s+', ' ', regex=True).str.strip()
            
        if 'เลือกชื่อผู้ปฏิบัติ' in df_log.columns:
            df_log['เลือกชื่อผู้ปฏิบัติ'] = df_log['เลือกชื่อผู้ปฏิบัติ'].astype(str).str.replace(r'\s+', ' ', regex=True).str.strip()
            
        if 'วันที่ปฏิบัติ' in df_log.columns:
            df_log['วันที่ปฏิบัติ'] = pd.to_datetime(df_log['วันที่ปฏิบัติ'], format='%d/%m/%Y', errors='coerce')
            
        return df_reg, df_log
        
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการโหลดข้อมูล: {e}")
        return pd.DataFrame(), pd.DataFrame()

def check_user_exists(df_reg, phone_number):
    """ฟังก์ชันสำหรับตรวจสอบเบอร์โทรศัพท์ตอนล็อกอิน"""
    if df_reg.empty or 'เบอร์ติดต่อ' not in df_reg.columns:
        return False, None
        
    match = df_reg[df_reg['เบอร์ติดต่อ'] == phone_number]
    if not match.empty:
        return True, match.iloc[0]['ชื่อ_นามสกุล']
    return False, None

def calculate_user_stats(df_log, user_name):
    """คำนวณสถิติตามเกณฑ์: ต้องต่อเนื่อง 30 วันก่อน แล้วเช็คนาทีรวมใน 30 วันนั้นว่า >= 360 หรือไม่ (เลือกกรอบแรกสุดหากคะแนนเท่ากัน)"""
    user_log = df_log[df_log['เลือกชื่อผู้ปฏิบัติ'] == user_name].copy()
    
    if user_log.empty:
        return {
            "total_minutes": 0, "total_days": 0, 
            "max_streak_days": 0, "minutes_in_max_streak": 0,
            "max_streak_period": "-",
            "is_certified": False, "cert_window_minutes": 0,
            "cert_window_start": "-", "cert_window_end": "-",
            "log_data": user_log
        }

    user_log = user_log.sort_values(by='วันที่ปฏิบัติ')
    total_minutes = int(user_log['รวมของวันนั้น'].sum() * 5)
    total_days = len(user_log['วันที่ปฏิบัติ'].dt.date.unique())
    
    daily_series = user_log.groupby(user_log['วันที่ปฏิบัติ'].dt.date)['รวมของวันนั้น'].sum()
    daily_series.index = pd.to_datetime(daily_series.index)
    
    if daily_series.empty:
        return {
            "total_minutes": total_minutes, "total_days": total_days, 
            "max_streak_days": 0, "minutes_in_max_streak": 0,
            "max_streak_period": "-",
            "is_certified": False, "cert_window_minutes": 0,
            "cert_window_start": "-", "cert_window_end": "-",
            "log_data": user_log
        }

    min_date = daily_series.index.min()
    max_date = daily_series.index.max()
    full_date_range = pd.date_range(start=min_date, end=max_date)
    daily_full = daily_series.reindex(full_date_range, fill_value=0)

    # 1. หาวันที่ต่อเนื่องสูงสุด (Max Streak) + จับวันที่เริ่มต้นและสิ้นสุด
    current_streak = 0
    current_streak_mins = 0
    current_start = None
    
    max_streak = 0
    max_streak_mins = 0
    max_start = None
    max_end = None

    for date, sessions in daily_full.items():
        if sessions > 0:
            if current_streak == 0:
                current_start = date
            current_streak += 1
            current_streak_mins += (sessions * 5)
        else:
            if current_streak > max_streak:
                max_streak = current_streak
                max_streak_mins = current_streak_mins
                max_start = current_start
                max_end = date - pd.Timedelta(days=1)
            elif current_streak == max_streak and current_streak > 0:
                if current_streak_mins > max_streak_mins:
                    max_streak_mins = current_streak_mins
                    max_start = current_start
                    max_end = date - pd.Timedelta(days=1)
            
            current_streak = 0
            current_streak_mins = 0
            current_start = None
            
    if current_streak > max_streak:
        max_streak = current_streak
        max_streak_mins = current_streak_mins
        max_start = current_start
        max_end = daily_full.index[-1]
    elif current_streak == max_streak and current_streak > 0:
        if current_streak_mins > max_streak_mins:
            max_streak_mins = current_streak_mins
            max_start = current_start
            max_end = daily_full.index[-1]

    if max_streak > 0:
        start_str = max_start.strftime("%d/%m/%Y")
        end_str = max_end.strftime("%d/%m/%Y")
        max_streak_period = f"{start_str} - {end_str}" if max_streak > 1 else start_str
    else:
        max_streak_period = "-"

    # 2. เช็คเกณฑ์ผ่าน (ต่อเนื่อง 30 วัน + นาที >= 360) โดยเลือกแสดงกรอบที่คะแนนสูงสุด (เอาอันแรกสุดถ้าคะแนนเท่ากัน)
    is_certified = False
    cert_window_start = "-"
    cert_window_end = "-"
    cert_window_minutes = 0
    
    if len(daily_full) >= 30:
        active_days_rolling = (daily_full > 0).rolling(window=30).sum()
        minutes_rolling = (daily_full * 5).rolling(window=30).sum()
        
        perfect_30d_streaks = (active_days_rolling == 30)
        
        # กรณี 1: มีช่วงที่ทำต่อเนื่องครบ 30 วัน
        if perfect_30d_streaks.any():
            valid_windows = minutes_rolling[perfect_30d_streaks]
            max_val = valid_windows.max()
            
            # ใช้ .index[0] เพื่อดึงกรอบเวลาแรกสุดที่ทำคะแนนได้เท่ากับ max_val
            best_end_date = valid_windows[valid_windows == max_val].index[0]
            
            cert_window_minutes = int(max_val)
            best_start_date = best_end_date - pd.Timedelta(days=29)
            cert_window_start = best_start_date.strftime("%d/%m/%Y")
            cert_window_end = best_end_date.strftime("%d/%m/%Y")
            
            if cert_window_minutes >= 360:
                is_certified = True
                
        # กรณี 2: ยังไม่มีช่วงไหนต่อเนื่องครบ 30 วัน (โชว์ความก้าวหน้า ไม่ให้ค่าเป็น 0)
        else:
            max_val = minutes_rolling.max()
            if pd.notna(max_val) and max_val > 0:
                # ดึงช่วงแรกสุดที่ได้คะแนนสูงสุด
                best_end_date = minutes_rolling[minutes_rolling == max_val].index[0]
                cert_window_minutes = int(max_val)
                best_start_date = best_end_date - pd.Timedelta(days=29)
                cert_window_start = best_start_date.strftime("%d/%m/%Y")
                cert_window_end = best_end_date.strftime("%d/%m/%Y")
    else:
        # กรณี 3: ประวัติรวมตั้งแต่วันแรกถึงวันล่าสุดยังไม่ถึง 30 วัน
        if daily_full.sum() > 0:
            cert_window_minutes = int(daily_full.sum() * 5)
            cert_window_start = min_date.strftime("%d/%m/%Y")
            cert_window_end = max_date.strftime("%d/%m/%Y")
                
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
        "log_data": user_log 
    }

def calculate_admin_stats(df_log):
    if df_log.empty:
        return {"total_users": 0, "total_minutes": 0}
        
    return {
        "total_users": df_log['เลือกชื่อผู้ปฏิบัติ'].nunique(),
        "total_minutes": int(df_log['รวมของวันนั้น'].sum() * 5),
    }