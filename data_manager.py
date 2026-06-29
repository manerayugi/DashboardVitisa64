import pandas as pd
import streamlit as st
import datetime

@st.cache_data(ttl=600)
def load_data():
    """ดึงข้อมูลจาก Google Sheets ผ่าน URL ที่กำหนดใน secrets"""
    try:
        reg_url = st.secrets["sheets"]["reg_url"]
        log_url = st.secrets["sheets"]["log_url"]
        
        df_reg = pd.read_csv(reg_url)
        df_log = pd.read_csv(log_url)
        
        # --- Data Cleaning ฝั่งฟอร์มสมัคร ---
        if 'เบอร์ติดต่อ' in df_reg.columns:
            # 1. แปลงเป็น string และลบทศนิยม (เผื่อ pandas อ่านมาเป็น float เช่น 889655939.0)
            df_reg['เบอร์ติดต่อ'] = df_reg['เบอร์ติดต่อ'].astype(str).str.replace(r'\.0$', '', regex=True)
            # 2. ลบตัวอักษรที่ไม่ใช่ตัวเลขออกทั้งหมด
            df_reg['เบอร์ติดต่อ'] = df_reg['เบอร์ติดต่อ'].str.replace(r'\D', '', regex=True)
            # 3. เติมเลข 0 ด้านหน้าให้ครบ 10 หลัก (แก้ปัญหา CSV ตัดเลข 0 ทิ้ง)
            df_reg['เบอร์ติดต่อ'] = df_reg['เบอร์ติดต่อ'].str.zfill(10)
            
        if 'ชื่อ_นามสกุล' in df_reg.columns:
            # ยุบช่องว่างที่เคาะซ้ำกันหลายทีให้เหลือเคาะเดียว และตัดช่องว่างหัวท้าย
            df_reg['ชื่อ_นามสกุล'] = df_reg['ชื่อ_นามสกุล'].astype(str).str.replace(r'\s+', ' ', regex=True).str.strip()
            
        # --- Data Cleaning ฝั่งฟอร์มบันทึกผล ---
        if 'เลือกชื่อผู้ปฏิบัติ' in df_log.columns:
            df_log['เลือกชื่อผู้ปฏิบัติ'] = df_log['เลือกชื่อผู้ปฏิบัติ'].astype(str).str.replace(r'\s+', ' ', regex=True).str.strip()
            
        # แปลงคอลัมน์วันที่ให้เป็นชนิดข้อมูล Datetime
        if 'วันที่ปฏิบัติ' in df_log.columns:
            df_log['วันที่ปฏิบัติ'] = pd.to_datetime(df_log['วันที่ปฏิบัติ'], format='%d/%m/%Y', errors='coerce')
            
        return df_reg, df_log
        
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการโหลดข้อมูล: {e}")
        return pd.DataFrame(), pd.DataFrame()

def check_user_exists(df_reg, phone_number):
    """ตรวจสอบเบอร์โทรศัพท์และดึงชื่อผู้ใช้งาน"""
    match = df_reg[df_reg['เบอร์ติดต่อ'] == phone_number]
    
    if not match.empty:
        user_name = match.iloc[0]['ชื่อ_นามสกุล']
        return True, user_name
    return False, None

def calculate_user_stats(df_log, user_name):
    """คำนวณสถิติส่วนตัวของผู้เข้าร่วมแต่ละคน ทั้งแบบทำต่อเนื่องทั่วไป และแบบปฏิบัติครบ 3 เวลา"""
    user_log = df_log[df_log['เลือกชื่อผู้ปฏิบัติ'] == user_name].copy()
    
    if user_log.empty:
        return {
            "total_minutes": 0, 
            "total_days": 0, 
            "max_streak_any": 0, 
            "any_start": "-",
            "any_end": "-",
            "streak_period_any": "-",
            "max_streak_perfect": 0, 
            "perfect_start": "-", 
            "perfect_end": "-", 
            "streak_period_perfect": "-",
            "log_data": user_log
        }

    # เรียงลำดับตามวันที่จากเก่าไปใหม่
    user_log = user_log.sort_values(by='วันที่ปฏิบัติ')
    
    # คำนวณยอดรวม (1 ครั้ง = 5 นาที)
    total_sessions = user_log['รวมของวันนั้น'].sum()
    total_minutes = total_sessions * 5
    total_days = len(user_log)
    
    # ฟังก์ชันภายในช่วยคำนวณ Streak และดึงข้อมูลวันที่เริ่มต้น/สิ้นสุด
    def get_streak_info(dates):
        if len(dates) == 0:
            return 0, "-", "-", "-"
            
        dates = sorted(dates)
        current_streak, current_start = 1, dates[0]
        max_streak, max_start, max_end = 1, dates[0], dates[0]
        
        for i in range(1, len(dates)):
            if (dates[i] - dates[i-1]).days == 1:
                current_streak += 1
            else:
                current_streak, current_start = 1, dates[i]
            
            if current_streak >= max_streak:
                max_streak = current_streak
                max_start = current_start
                max_end = dates[i]
        
        start_str = max_start.strftime("%d/%m/%Y")
        end_str = max_end.strftime("%d/%m/%Y")
        period = f"{start_str} - {end_str}" if max_streak > 1 else start_str
        
        return max_streak, start_str, end_str, period

    # 1. คำนวณทำต่อเนื่องแบบเก่า (นับทุกวันที่มีการบันทึกผลเข้ามาอย่างน้อย 1 รอบ)
    valid_dates_any = user_log['วันที่ปฏิบัติ'].dropna().dt.date.unique()
    max_streak_any, any_start, any_end, streak_period_any = get_streak_info(valid_dates_any)
    
    # 2. คำนวณทำต่อเนื่องแบบใหม่ (นับเฉพาะวันที่ปฏิบัติครบ 3 ครั้งขึ้นไปเท่านั้น)
    valid_dates_perfect = user_log[user_log['รวมของวันนั้น'] >= 3]['วันที่ปฏิบัติ'].dropna().dt.date.unique()
    max_streak_perfect, perfect_start, perfect_end, streak_period_perfect = get_streak_info(valid_dates_perfect)
                
    return {
        "total_minutes": total_minutes,
        "total_days": total_days,
        "max_streak_any": max_streak_any,
        "any_start": any_start,
        "any_end": any_end,
        "streak_period_any": streak_period_any,
        "max_streak_perfect": max_streak_perfect,
        "perfect_start": perfect_start,
        "perfect_end": perfect_end,
        "streak_period_perfect": streak_period_perfect,
        "log_data": user_log 
    }

def calculate_admin_stats(df_log):
    """คำนวณสถิติภาพรวมสำหรับ Admin"""
    if df_log.empty:
        return {"total_users": 0, "total_minutes": 0}
        
    total_users = df_log['เลือกชื่อผู้ปฏิบัติ'].nunique()
    total_sessions = df_log['รวมของวันนั้น'].sum()
    total_minutes = total_sessions * 5
    
    return {
        "total_users": total_users,
        "total_minutes": total_minutes,
    }