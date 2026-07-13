"""โหลดและทำความสะอาดข้อมูลดิบจาก Google Sheets (ฟอร์มลงทะเบียน + ฟอร์มบันทึกผล)

ไฟล์นี้รับผิดชอบเฉพาะเรื่อง "เอาข้อมูลเข้ามา" และ "ทำความสะอาดให้อยู่ในรูปแบบที่ใช้งานได้"
ส่วนการคำนวณสถิติ/เกียรติบัตรอยู่ใน stats.py
"""
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import streamlit as st


@st.cache_data(ttl=600)
def load_data():
    """ดึงข้อมูลฟอร์มลงทะเบียนและฟอร์มบันทึกผลจาก Google Sheets แบบ Export CSV

    ยิง request ทั้ง 2 ชีตพร้อมกัน (I/O-bound) แทนที่จะรอทีละอัน เพื่อลดเวลาตอน cache หมดอายุ
    แคชผลลัพธ์ไว้ 10 นาที (ttl=600) เพื่อลดจำนวนครั้งที่ต้องยิง request ไปที่ Google Sheets
    เรียก load_data.clear() เพื่อบังคับให้โหลดข้อมูลใหม่ (ใช้ในปุ่ม "โหลดข้อมูลใหม่" ที่ app.py)
    """
    try:
        reg_url = st.secrets["sheets"]["reg_url"]
        log_url = st.secrets["sheets"]["log_url"]

        with ThreadPoolExecutor(max_workers=2) as executor:
            reg_future = executor.submit(pd.read_csv, reg_url)
            log_future = executor.submit(pd.read_csv, log_url)
            df_reg = reg_future.result()
            df_log = log_future.result()

        _clean_registration_df(df_reg)
        _clean_log_df(df_log)

        return df_reg, df_log

    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการโหลดข้อมูล: {e}")
        return pd.DataFrame(), pd.DataFrame()


def _clean_registration_df(df_reg):
    """ทำความสะอาดข้อมูลฟอร์มลงทะเบียน (แก้ไข DataFrame ที่รับเข้ามาโดยตรง)

    - เบอร์ติดต่อ: ตัด ".0" ที่ติดมาจาก Google Sheets ตีความเป็นตัวเลข, ลบอักขระที่ไม่ใช่ตัวเลข,
      แล้วเติม 0 ข้างหน้าให้ครบ 10 หลัก เพื่อให้เทียบกับเบอร์ที่ผู้ใช้กรอกตอน login ได้ตรงกันเป๊ะ
    - ชื่อ_นามสกุล: รวมช่องว่างซ้ำและตัดช่องว่างหัวท้าย เพื่อให้ match กับชื่อในฟอร์มบันทึกผลได้แม่นยำ
    """
    if 'เบอร์ติดต่อ' in df_reg.columns:
        df_reg['เบอร์ติดต่อ'] = df_reg['เบอร์ติดต่อ'].astype(str).str.replace(r'\.0$', '', regex=True)
        df_reg['เบอร์ติดต่อ'] = df_reg['เบอร์ติดต่อ'].str.replace(r'\D', '', regex=True).str.zfill(10)

    if 'ชื่อ_นามสกุล' in df_reg.columns:
        df_reg['ชื่อ_นามสกุล'] = df_reg['ชื่อ_นามสกุล'].astype(str).str.replace(r'\s+', ' ', regex=True).str.strip()


def _clean_log_df(df_log):
    """ทำความสะอาดข้อมูลฟอร์มบันทึกผล (แก้ไข DataFrame ที่รับเข้ามาโดยตรง)"""
    if 'เลือกชื่อผู้ปฏิบัติ' in df_log.columns:
        df_log['เลือกชื่อผู้ปฏิบัติ'] = df_log['เลือกชื่อผู้ปฏิบัติ'].astype(str).str.replace(r'\s+', ' ', regex=True).str.strip()

    if 'วันที่ปฏิบัติ' in df_log.columns:
        df_log['วันที่ปฏิบัติ'] = pd.to_datetime(df_log['วันที่ปฏิบัติ'], format='%d/%m/%Y', errors='coerce')


def check_user_exists(df_reg, phone_number):
    """ตรวจสอบเบอร์โทรศัพท์ตอน login ว่าตรงกับผู้ลงทะเบียนคนใดหรือไม่

    คืนค่า (True, ชื่อ_นามสกุล) ถ้าพบ, มิฉะนั้นคืนค่า (False, None)
    """
    if df_reg.empty or 'เบอร์ติดต่อ' not in df_reg.columns:
        return False, None

    match = df_reg[df_reg['เบอร์ติดต่อ'] == phone_number]
    if not match.empty:
        return True, match.iloc[0]['ชื่อ_นามสกุล']
    return False, None
