"""โหลดและทำความสะอาดข้อมูลขององค์กรภายนอก (แยกจากโครงการวิทิสาสมาธิ64)

มี 2 แหล่งข้อมูล:
- log_url: ฟอร์มบันทึกผลรายวัน (ใช้คำนวณ streak ความต่อเนื่อง + นาทีสะสม)
- reg_url: ทะเบียนจำนวนคนที่สมัครไว้ต่อบริษัท (ใช้แสดงยอดสมัครเทียบกับยอดที่บันทึกจริง)
"""
import pandas as pd
import streamlit as st


@st.cache_data(ttl=600)
def load_org_data():
    """ดึงข้อมูลบันทึกผลรายวันขององค์กรภายนอกจาก Google Sheets แบบ Export CSV

    แคชผลลัพธ์ไว้ 10 นาทีเหมือน data_loader.load_data() เรียก load_org_data.clear() เพื่อบังคับโหลดใหม่
    """
    try:
        org_url = st.secrets["org"]["log_url"]
        df = pd.read_csv(org_url)
        return _clean_org_log_df(df)
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการโหลดข้อมูลบันทึกผลองค์กร: {e}")
        return pd.DataFrame(columns=['บริษัท', 'วันที่ทำ', 'เบอร์โทร'])


@st.cache_data(ttl=600)
def load_org_registration():
    """ดึงทะเบียนจำนวนคนที่สมัครไว้ต่อบริษัทจาก Google Sheets แบบ Export CSV"""
    try:
        reg_url = st.secrets["org"]["reg_url"]
        df = pd.read_csv(reg_url)
        return _clean_org_reg_df(df)
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการโหลดทะเบียนองค์กร: {e}")
        return pd.DataFrame(columns=['บริษัท', 'จำนวนคนสมัคร'])


def _clean_org_log_df(df):
    """ทำความสะอาด: เหลือคอลัมน์บริษัท + วันที่ + เบอร์โทร แล้ว dedupe เหลือ 1 แถวต่อ (เบอร์โทร, วันที่)

    กันกรณีคนคนเดียวส่งฟอร์มซ้ำวันเดียวกัน (เช่น แก้ไขข้อมูลทีหลัง) โดยเก็บแค่ครั้งล่าสุดตาม timestamp
    เพื่อไม่ให้นาทีสะสม/จำนวนคนถูกนับซ้ำ
    """
    company_col = 'ชื่อหน่วยงาน / บริษัท'
    date_col = 'รายงานประจำวันที่'
    phone_col = 'หมายเลขโทรศัพท์ติดต่อ'
    ts_col = 'ประทับเวลา'

    required = [company_col, date_col, phone_col, ts_col]
    if not all(c in df.columns for c in required):
        return pd.DataFrame(columns=['บริษัท', 'วันที่ทำ', 'เบอร์โทร'])

    df = df[required].copy()
    df.columns = ['บริษัท', 'วันที่ทำ', 'เบอร์โทร', 'ประทับเวลา']
    df['บริษัท'] = df['บริษัท'].astype(str).str.strip()
    df['เบอร์โทร'] = df['เบอร์โทร'].astype(str).str.replace(r'\D', '', regex=True)
    df['วันที่ทำ'] = pd.to_datetime(df['วันที่ทำ'], format='%d/%m/%Y', errors='coerce')
    df['ประทับเวลา'] = pd.to_datetime(df['ประทับเวลา'], dayfirst=True, errors='coerce')

    df = df.dropna(subset=['วันที่ทำ'])
    df = df.sort_values('ประทับเวลา').drop_duplicates(subset=['เบอร์โทร', 'วันที่ทำ'], keep='last')

    return df[['บริษัท', 'วันที่ทำ', 'เบอร์โทร']].reset_index(drop=True)


def _clean_org_reg_df(df):
    """ทำความสะอาด: เหลือคอลัมน์ชื่อบริษัท + จำนวนคนที่สมัครไว้ (คอลัมน์ 'รวม' ในทะเบียน)"""
    company_col = 'ชื่อบริษัท'
    total_col = 'รวม'

    if company_col not in df.columns or total_col not in df.columns:
        return pd.DataFrame(columns=['บริษัท', 'จำนวนคนสมัคร'])

    df = df[[company_col, total_col]].copy()
    df.columns = ['บริษัท', 'จำนวนคนสมัคร']
    df['บริษัท'] = df['บริษัท'].astype(str).str.strip()
    df['จำนวนคนสมัคร'] = pd.to_numeric(df['จำนวนคนสมัคร'], errors='coerce').fillna(0).astype(int)

    return df
