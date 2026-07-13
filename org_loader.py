"""โหลดและทำความสะอาดข้อมูลบันทึกผลขององค์กรภายนอก (แยกจากโครงการวิทิสาสมาธิ64)

เก็บเฉพาะระดับ "บริษัท + วันที่ทำ" เท่านั้น ไม่สนชื่อผู้บันทึก/เบอร์โทร เพราะดูภาพรวม
ความต่อเนื่องขององค์กร ไม่ใช่รายบุคคล (และข้อมูลดิบมีชื่อ/เบอร์โทรพิมพ์ไม่ตรงกันในแต่ละครั้งด้วย)
"""
import pandas as pd
import streamlit as st


@st.cache_data(ttl=600)
def load_org_data():
    """ดึงข้อมูลบันทึกผลขององค์กรภายนอกจาก Google Sheets แบบ Export CSV

    แคชผลลัพธ์ไว้ 10 นาทีเหมือน data_loader.load_data() เรียก load_org_data.clear() เพื่อบังคับโหลดใหม่
    """
    try:
        org_url = st.secrets["org"]["log_url"]
        df = pd.read_csv(org_url)
        return _clean_org_df(df)
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการโหลดข้อมูลองค์กร: {e}")
        return pd.DataFrame(columns=['บริษัท', 'วันที่ทำ'])


def _clean_org_df(df):
    """ทำความสะอาด: เหลือแค่คอลัมน์บริษัท + วันที่ แล้ว dedupe ให้เหลือ 1 แถวต่อบริษัทต่อวัน

    ถือว่าวันนั้น "ทำแล้ว" ถ้ามีอย่างน้อย 1 คนในบริษัทส่งฟอร์มมา ไม่ว่าจะกี่คน/กี่ช่วงก็ตาม
    """
    company_col = 'ชื่อหน่วยงาน / บริษัท'
    date_col = 'รายงานประจำวันที่'

    if company_col not in df.columns or date_col not in df.columns:
        return pd.DataFrame(columns=['บริษัท', 'วันที่ทำ'])

    df = df[[company_col, date_col]].copy()
    df.columns = ['บริษัท', 'วันที่ทำ']
    df['บริษัท'] = df['บริษัท'].astype(str).str.strip()
    df['วันที่ทำ'] = pd.to_datetime(df['วันที่ทำ'], format='%d/%m/%Y', errors='coerce')

    df = df.dropna(subset=['วันที่ทำ'])
    df = df.drop_duplicates(subset=['บริษัท', 'วันที่ทำ'])

    return df
