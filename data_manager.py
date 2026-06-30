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
        
        # ปรับรูปแบบข้อมูล
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

def calculate_user_stats(df_log, user_name):
    user_log = df_log[df_log['เลือกชื่อผู้ปฏิบัติ'] == user_name].copy()
    
    # ค่าเริ่มต้น
    stats = {
        "total_minutes": 0, "total_days": 0, 
        "max_streak_days": 0, "minutes_in_max_streak": 0,
        "max_streak_period": "-",
        "is_certified": False, "cert_window_minutes": 0,
        "cert_window_start": "-", "cert_window_end": "-",
        "log_data": user_log
    }

    if user_log.empty:
        return stats

    user_log = user_log.sort_values(by='วันที่ปฏิบัติ')
    stats["total_minutes"] = int(user_log['รวมของวันนั้น'].sum() * 5)
    stats["total_days"] = len(user_log['วันที่ปฏิบัติ'].dt.date.unique())
    
    daily_series = user_log.groupby(user_log['วันที่ปฏิบัติ'].dt.date)['รวมของวันนั้น'].sum()
    daily_series.index = pd.to_datetime(daily_series.index)
    
    min_date, max_date = daily_series.index.min(), daily_series.index.max()
    daily_full = daily_series.reindex(pd.date_range(start=min_date, end=max_date), fill_value=0)

    # 1. คำนวณ Streak ต่อเนื่อง
    current_streak = 0
    current_streak_mins = 0
    current_start = None
    max_streak, max_streak_mins, max_start, max_end = 0, 0, None, None

    for date, sessions in daily_full.items():
        if sessions > 0:
            if current_streak == 0: current_start = date
            current_streak += 1
            current_streak_mins += (sessions * 5)
        else:
            if current_streak > max_streak:
                max_streak, max_streak_mins, max_start, max_end = current_streak, current_streak_mins, current_start, date - pd.Timedelta(days=1)
            current_streak, current_streak_mins, current_start = 0, 0, None
            
    if current_streak > max_streak:
        max_streak, max_streak_mins, max_start, max_end = current_streak, current_streak_mins, current_start, daily_full.index[-1]

    stats["max_streak_days"] = max_streak
    stats["minutes_in_max_streak"] = max_streak_mins
    stats["max_streak_period"] = f"{max_start.strftime('%d/%m/%Y')} - {max_end.strftime('%d/%m/%Y')}" if max_streak > 0 else "-"

    # 2. ตรวจสอบเงื่อนไข 30 วัน
    if len(daily_full) >= 30:
        active_days_rolling = (daily_full > 0).rolling(window=30).sum()
        minutes_rolling = (daily_full * 5).rolling(window=30).sum()
        
        # เงื่อนไขผ่านเกณฑ์: ต่อเนื่อง 30 วัน และนาที >= 360
        perfect_30d = (active_days_rolling == 30)
        
        if perfect_30d.any():
            # หาจุดที่นาทีสะสมเกิน 360 ในกลุ่มที่ต่อเนื่อง 30 วัน
            candidates = minutes_rolling[perfect_30d]
            if (candidates >= 360).any():
                best_end_date = candidates[candidates >= 360].index[0] # เลือกจุดแรกที่ผ่านเกณฑ์
                stats["is_certified"] = True
                stats["cert_window_minutes"] = int(minutes_rolling[best_end_date])
                stats["cert_window_start"] = (best_end_date - pd.Timedelta(days=29)).strftime("%d/%m/%Y")
                stats["cert_window_end"] = best_end_date.strftime("%d/%m/%Y")
            else:
                # ยังไม่ครบ 360 แต่ต่อเนื่อง 30 วันแล้ว (โชว์ข้อมูลความก้าวหน้า)
                best_end_date = candidates.idxmax()
                stats["cert_window_minutes"] = int(minutes_rolling[best_end_date])
                stats["cert_window_start"] = (best_end_date - pd.Timedelta(days=29)).strftime("%d/%m/%Y")
                stats["cert_window_end"] = best_end_date.strftime("%d/%m/%Y")

    return stats

def calculate_admin_stats(df_log):
    if df_log.empty:
        return {"total_users": 0, "total_minutes": 0}
    return {
        "total_users": df_log['เลือกชื่อผู้ปฏิบัติ'].nunique(),
        "total_minutes": int(df_log['รวมของวันนั้น'].sum() * 5),
    }