"""ไฟล์หลัก (Main/Routing): จัดการ session, sidebar, และสลับหน้าจอตามสิทธิ์ผู้ใช้"""
import datetime

import streamlit as st

import auth
import config
import data_loader
import org_loader
from ui.admin_view import admin_dashboard
from ui.org_view import org_dashboard
from ui.user_view import user_dashboard

st.set_page_config(page_title="Dashboard วิทิสาสมาธิ64", page_icon="🧘‍♂️", layout="wide")


def _render_sidebar():
    """Sidebar: ทักทาย, ปุ่มโหลดข้อมูลใหม่ (เคลียร์ cache), และปุ่มออกจากระบบ"""
    with st.sidebar:
        st.write(f"สวัสดี, **{st.session_state['username']}**")
        if st.session_state.get("is_admin"):
            st.success("👑 สิทธิ์ผู้ดูแลระบบ")

        st.divider()

        st.write("🔄 **อัปเดตข้อมูล**")
        if 'last_refresh' not in st.session_state:
            st.session_state['last_refresh'] = datetime.datetime.now(config.TZ_TH).strftime("%d/%m/%Y %H:%M:%S")

        st.caption(f"ล่าสุด: {st.session_state['last_refresh']}")

        if st.button("โหลดข้อมูลใหม่", use_container_width=True):
            data_loader.load_data.clear()  # สั่งเคลียร์ Cache ของฟังก์ชันดึงข้อมูล
            org_loader.load_org_data.clear()
            org_loader.load_org_registration.clear()
            st.session_state['last_refresh'] = datetime.datetime.now(config.TZ_TH).strftime("%d/%m/%Y %H:%M:%S")
            st.rerun()

        st.divider()
        if st.button("🚪 ออกจากระบบ", use_container_width=True):
            st.session_state.clear()
            st.rerun()


def _render_admin_tabs(df_reg, df_log):
    tab_user, tab_admin, tab_org = st.tabs(["👤 ข้อมูลรายบุคคล", "👑 ภาพรวมโครงการ (Admin)", "🏢 องค์กรภายนอก (Admin)"])

    with tab_user:
        if df_reg is not None:
            user_list = sorted(df_reg['ชื่อ_นามสกุล'].dropna().unique().tolist())
            default_idx = user_list.index(st.session_state['username']) if st.session_state['username'] in user_list else 0
            selected_user = st.selectbox("🔍 เลือกผู้ปฏิบัติสมาธิเพื่อดูข้อมูล:", user_list, index=default_idx)
            user_dashboard(df_log, selected_user)

    with tab_admin:
        admin_dashboard(df_reg, df_log)

    with tab_org:
        # เรียกใน _render_admin_tabs (แอดมินเท่านั้น) ผู้ใช้ทั่วไปจะไม่โดนดึงข้อมูลนี้เลย
        org_dashboard(org_loader.load_org_data(), org_loader.load_org_registration())


def _render_user_tab(df_log):
    tab_user, = st.tabs(["👤 ข้อมูลส่วนตัว"])
    with tab_user:
        user_dashboard(df_log, st.session_state['username'])


def main():
    # โหลดข้อมูลมารอไว้เลยตั้งแต่เปิดหน้าเว็บ (เพื่อสร้าง Cache ทันที)
    # load_data() ดักข้อผิดพลาดเองแล้ว จะคืน DataFrame ว่างแทนการโยน exception ออกมา
    df_reg, df_log = data_loader.load_data()

    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False

    if not st.session_state["logged_in"]:
        auth.login_page()
        return

    _render_sidebar()

    # ควบคุมการแสดงผลตามสิทธิ์
    if st.session_state.get("is_admin", False):
        _render_admin_tabs(df_reg, df_log)
    else:
        _render_user_tab(df_log)


if __name__ == "__main__":
    main()
