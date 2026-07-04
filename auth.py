"""ระบบเข้าสู่ระบบแบบ Single-key: ใช้เบอร์โทรศัพท์ที่ลงทะเบียนไว้ หรือรหัสผ่านแอดมิน"""
import re

import streamlit as st

import data_loader

try:
    # รายชื่อ/รหัสแอดมินระดับสูง (ไม่ต้องลงทะเบียนเป็นผู้เข้าร่วมก็เข้าได้)
    ADMIN_NUMBERS = st.secrets["admin"]["phone_numbers"]
except Exception:
    ADMIN_NUMBERS = []

def login_page():
    """แสดงฟอร์ม login กึ่งกลางหน้าจอ พร้อมเช็คว่าเป็นผู้เข้าร่วม/แอดมินหรือไม่"""
    _, center_col, _ = st.columns([1, 2, 1])
    with center_col:
        _, logo_col, _ = st.columns([1, 2, 1])
        with logo_col:
            try:
                st.image("assets/logo.png", use_container_width=True)
            except Exception:
                pass  # ไม่มีโลโก้ก็ไม่เป็นไร ข้ามไปแสดงหัวข้อต่อ
        
        st.markdown("<h1 style='text-align: center;'>🧘‍♂️ วิทิสาสมาธิ64</h1>", unsafe_allow_html=True)
        st.markdown("<h3 style='text-align: center;'>กรุณาเข้าสู่ระบบ</h3>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center;'>ใช้ <b>เบอร์โทรศัพท์</b> (หรือรหัสผ่านสำหรับแอดมิน)</p>", unsafe_allow_html=True)

        password_input = st.text_input("รหัสเข้าสู่ระบบ", type="password")

        if st.button("เข้าสู่ระบบ", use_container_width=True):
            if password_input:
                df_reg, _ = data_loader.load_data()

                # ทำความสะอาด input เผื่อผู้ใช้พิมพ์มาเป็นเบอร์โทร
                clean_phone = re.sub(r'\D', '', password_input).zfill(10)

                # 1. เช็คว่าเป็นผู้เข้าร่วมในระบบหรือไม่
                is_participant, user_name = data_loader.check_user_exists(df_reg, clean_phone)
                
                # 2. เช็คว่ามีสิทธิ์เป็นแอดมินหรือไม่ (เช็คทั้งแบบดิบๆ และแบบเบอร์โทร)
                is_admin = (password_input in ADMIN_NUMBERS) or (clean_phone in ADMIN_NUMBERS)

                if is_participant:
                    # กรณีเป็นผู้เข้าร่วม (อาจจะเป็นแอดมินหรือไม่ก็ได้)
                    st.session_state["logged_in"] = True
                    st.session_state["username"] = user_name
                    st.session_state["is_admin"] = is_admin
                    st.rerun()
                elif is_admin:
                    # กรณีเป็นแอดมินระดับสูง (ไม่ได้ลงทะเบียนเป็นผู้เข้าร่วม)
                    st.session_state["logged_in"] = True
                    st.session_state["username"] = "Admin"
                    st.session_state["is_admin"] = True
                    st.rerun()
                else:
                    st.error("❌ ไม่พบข้อมูลในระบบ กรุณาตรวจสอบอีกครั้ง")
            else:
                st.warning("⚠️ กรุณากรอกรหัสเข้าสู่ระบบ")