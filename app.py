import streamlit as st
import data_manager as dm
import auth
import components
import datetime

st.set_page_config(page_title="Dashboard วิทิสาสมาธิ64", page_icon="🧘‍♂️", layout="wide")

def main():
    # โหลดข้อมูลมารอไว้เลยตั้งแต่เปิดหน้าเว็บ (เพื่อสร้าง Cache ทันที)
    try:
        df_reg, df_log = dm.load_data()
    except:
        df_reg, df_log = None, None

    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False

    if not st.session_state["logged_in"]:
        auth.login_page()
    else:
        # Sidebar
        with st.sidebar:
            st.write(f"สวัสดี, **{st.session_state['username']}**")
            if st.session_state.get("is_admin"):
                st.success("👑 สิทธิ์ผู้ดูแลระบบ")
            
            st.divider()
            
            # --- ส่วนของปุ่ม Refresh ---
            st.write("🔄 **อัปเดตข้อมูล**")
            if 'last_refresh' not in st.session_state:
                st.session_state['last_refresh'] = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                
            st.caption(f"ล่าสุด: {st.session_state['last_refresh']}")
            
            if st.button("โหลดข้อมูลใหม่", use_container_width=True):
                dm.load_data.clear() # สั่งเคลียร์ Cache ของฟังก์ชันดึงข้อมูล
                st.session_state['last_refresh'] = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                st.rerun() # รีเฟรชหน้าเว็บใหม่
                
            st.divider()
            if st.button("🚪 ออกจากระบบ", use_container_width=True):
                st.session_state.clear()
                st.rerun()

        # ควบคุมการแสดงผลตามสิทธิ์
        if st.session_state.get("is_admin", False):
            tab_user, tab_admin = st.tabs(["👤 ข้อมูลรายบุคคล", "👑 ภาพรวมโครงการ (Admin)"])
            
            with tab_user:
                if df_reg is not None:
                    user_list = df_reg['ชื่อ_นามสกุล'].dropna().unique().tolist()
                    user_list.sort() # เรียง ก-ฮ
                    default_idx = user_list.index(st.session_state['username']) if st.session_state['username'] in user_list else 0
                    selected_user = st.selectbox("🔍 เลือกผู้ปฏิบัติสมาธิเพื่อดูข้อมูล:", user_list, index=default_idx)
                    components.user_dashboard(df_log, selected_user)
                
            with tab_admin:
                components.admin_dashboard(df_reg, df_log)
                
        else:
            tab_user, = st.tabs(["👤 ข้อมูลส่วนตัว"])
            with tab_user:
                components.user_dashboard(df_log, st.session_state['username'])

if __name__ == "__main__":
    main()