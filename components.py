import streamlit as st
import data_manager as dm
import datetime
import calendar
import pandas as pd

# ⚙️ เปลี่ยนเป้าหมายเป็น "จำนวนวันที่ทำต่อเนื่อง"
CERT_TARGET_STREAK = 30

def render_calendar(user_log):
    st.subheader("📅 ปฏิทินการปฏิบัติสมาธิ")
    
    if not user_log.empty:
        latest_date = user_log['วันที่ปฏิบัติ'].max().date()
    else:
        latest_date = datetime.date.today()

    if 'cal_month' not in st.session_state:
        st.session_state.cal_month = latest_date.month
    if 'cal_year' not in st.session_state:
        st.session_state.cal_year = latest_date.year

    def prev_month():
        if st.session_state.cal_month == 1:
            st.session_state.cal_month = 12
            st.session_state.cal_year -= 1
        else: 
            st.session_state.cal_month -= 1

    def next_month():
        if st.session_state.cal_month == 12:
            st.session_state.cal_month = 1
            st.session_state.cal_year += 1
        else: 
            st.session_state.cal_month += 1

    head_col1, head_col2, head_col3 = st.columns([2, 4, 2])
    with head_col1: 
        st.button("◀️ Prev", on_click=prev_month, use_container_width=True, key="prev_cal")
    with head_col2:
        st.markdown(f"<h4 style='text-align:center; color:#374151; margin-top:5px;'>{calendar.month_name[st.session_state.cal_month]} {st.session_state.cal_year}</h4>", unsafe_allow_html=True)
    with head_col3: 
        st.button("Next ▶️", on_click=next_month, use_container_width=True, key="next_cal")

    calendar.setfirstweekday(calendar.SUNDAY)
    cal = calendar.monthcalendar(st.session_state.cal_year, st.session_state.cal_month)
    days_of_week = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
    
    if not user_log.empty:
        df_cal = user_log.copy()
        df_cal['Date'] = df_cal['วันที่ปฏิบัติ'].dt.date
        daily_stats = df_cal.groupby('Date').agg(Total_Sessions=('รวมของวันนั้น', 'sum')).to_dict('index')
    else:
        daily_stats = {}

    week_cols = st.columns(7)
    for idx, day_name in enumerate(days_of_week):
        week_cols[idx].markdown(f"<div style='text-align:center; font-weight:600; color:#9ca3af; font-size:12px; margin-bottom:8px;'>{day_name}</div>", unsafe_allow_html=True)

    today_date = datetime.date.today()

    for week in cal:
        day_cols = st.columns(7)
        for idx, day in enumerate(week):
            if day == 0:
                day_cols[idx].markdown("<div style='height:80px;'></div>", unsafe_allow_html=True)
            else:
                current_date = datetime.date(st.session_state.cal_year, st.session_state.cal_month, day)
                count = daily_stats.get(current_date, {}).get('Total_Sessions', 0)
                
                status_text = ""
                if count >= 3:
                    bg_color, border_color, text_color, status_text = "#ecfdf5", "#10b981", "#047857", "ครบ 3 ครั้ง"
                elif count in [1, 2]:
                    bg_color, border_color, text_color, status_text = "#fefce8", "#eab308", "#a16207", f"ทำ {int(count)} ครั้ง"
                else:
                    if current_date <= today_date:
                        bg_color, border_color, text_color, status_text = "#fef2f2", "#ef4444", "#b91c1c", "ไม่ได้ทำ"
                    else:
                        bg_color, border_color, text_color = "#ffffff", "#e5e7eb", "#d1d5db"

                if status_text != "":
                    day_cols[idx].markdown(f"""
                        <div style="position:relative; background-color:{bg_color}; border: 1px solid {border_color}; border-radius:8px; padding:6px; height:80px; display:flex; flex-direction:column; justify-content:center; align-items:center; box-shadow: 0 1px 2px rgba(0,0,0,0.05);">
                            <span style="position:absolute; top:4px; left:6px; font-size:11px; color:#374151; font-weight:600;">{day}</span>
                            <div style="text-align:center; line-height:1.2;">
                                <span style="font-size:11px; color:{text_color}; font-weight:700;">{status_text}</span><br>
                                <span style="font-size:10px; color:{text_color}; opacity: 0.8;">{int(count)*5} นาที</span>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                else:
                    day_cols[idx].markdown(f"""
                        <div style="position:relative; background-color:#ffffff; border: 1px solid #e5e7eb; border-radius:8px; padding:6px; height:80px; display:flex; flex-direction:column; justify-content:center; align-items:center;">
                            <span style="position:absolute; top:4px; left:6px; font-size:11px; color:#d1d5db; font-weight:500;">{day}</span>
                        </div>
                    """, unsafe_allow_html=True)

def style_status(val):
    if val == 'ทำแล้ว':
        return 'background-color: #dcfce7; color: #166534; font-weight: bold;'
    elif val == 'ไม่ได้ทำ':
        return 'background-color: #fee2e2; color: #991b1b;'
    return ''

def style_total_sessions(val):
    try:
        count = int(val)
        if count >= 3:
            return 'background-color: #ecfdf5; color: #047857; font-weight: bold;'
        elif count in [1, 2]:
            return 'background-color: #fefce8; color: #a16207; font-weight: bold;'
        else:
            return 'background-color: #fef2f2; color: #b91c1c; font-weight: bold;'
    except:
        return ''

def user_dashboard(df_log, target_username):
    st.header(f"สถิติของ: {target_username}")
    
    stats = dm.calculate_user_stats(df_log, target_username)
    
    # คำนวณเปอร์เซ็นต์ความสำเร็จ (ห้ามเกิน 1.0 หรือ 100%)
    progress_val = min(stats['max_streak'] / CERT_TARGET_STREAK, 1.0)
    
    if stats['max_streak'] >= CERT_TARGET_STREAK: 
        st.success(f"🎉 **ขอแสดงความยินดี!** ท่านปฏิบัติสมาธิติดต่อกันครบ {CERT_TARGET_STREAK} วัน และได้รับเกียรติบัตรแล้ว", icon="🏆")
        
        if 'balloons_shown' not in st.session_state:
            st.balloons()
            st.session_state['balloons_shown'] = True
    else:
        # 📊 แสดง Progress Bar สำหรับคนที่ยังไม่ผ่านเงื่อนไข
        st.markdown(f"**เป้าหมายเกียรติบัตร:** ทำสมาธิต่อเนื่อง {CERT_TARGET_STREAK} วัน (ปัจจุบันทำได้สูงสุด {stats['max_streak']} วัน)")
        st.progress(progress_val)
        
        # คำนวณว่าขาดอีกกี่วัน
        days_left = CERT_TARGET_STREAK - stats['max_streak']
        st.caption(f"🔥 สู้ๆ ครับ ขาดอีกเพียง **{days_left}** วันเท่านั้น!")
    
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric(label="⏱️ นาทีสะสมทั้งหมด", value=f"{stats['total_minutes']:,} นาที")
    with c2:
        st.metric(label="📅 จำนวนวันที่ปฏิบัติ", value=f"{stats['total_days']:,} วัน")
    with c3:
        st.metric(label="🔥 ทำต่อเนื่องสูงสุด", value=f"{stats['max_streak']:,} วัน", delta=stats['streak_period'], delta_color="off")
        
    st.divider()
    
    render_calendar(stats['log_data'])
    
    st.subheader("📋 ประวัติการบันทึกผล")
    if not stats['log_data'].empty:
        df_display = stats['log_data'][['วันที่ปฏิบัติ', 'max คะแนนรอบ เช้า', 'max คะแนนรอบ กลางวัน', 'max คะแนนรอบ เย็น', 'รวมของวันนั้น']].copy()
        
        df_display = df_display.rename(columns={
            'max คะแนนรอบ เช้า': 'เช้า',
            'max คะแนนรอบ กลางวัน': 'กลางวัน',
            'max คะแนนรอบ เย็น': 'เย็น'
        })
        
        df_display['วันที่ปฏิบัติ'] = df_display['วันที่ปฏิบัติ'].dt.strftime('%d/%m/%Y')
        
        for col in ['เช้า', 'กลางวัน', 'เย็น']:
            df_display[col] = df_display[col].apply(lambda x: 'ทำแล้ว' if x == 1 else 'ไม่ได้ทำ')
            
        try:
            styled_df = df_display.style\
                .map(style_status, subset=['เช้า', 'กลางวัน', 'เย็น'])\
                .map(style_total_sessions, subset=['รวมของวันนั้น'])
        except AttributeError:
            styled_df = df_display.style\
                .applymap(style_status, subset=['เช้า', 'กลางวัน', 'เย็น'])\
                .applymap(style_total_sessions, subset=['รวมของวันนั้น'])
            
        st.dataframe(styled_df, use_container_width=True, hide_index=True)
    else:
        st.info("ยังไม่มีข้อมูลการบันทึกผลสมาธิครับ")

def admin_dashboard(df_reg, df_log):
    st.header("👑 Admin Dashboard: ภาพรวมโครงการ")
    
    admin_stats = dm.calculate_admin_stats(df_log)
    total_registered = len(df_reg['ชื่อ_นามสกุล'].dropna().unique()) if not df_reg.empty else 0
    
    # ดึงชื่อผู้เข้าร่วมจากทั้ง 2 ไฟล์เพื่อป้องกันคนตกหล่น
    all_users = set()
    if df_reg is not None and not df_reg.empty and 'ชื่อ_นามสกุล' in df_reg.columns:
        all_users.update(df_reg['ชื่อ_นามสกุล'].dropna().tolist())
    if df_log is not None and not df_log.empty and 'เลือกชื่อผู้ปฏิบัติ' in df_log.columns:
        all_users.update(df_log['เลือกชื่อผู้ปฏิบัติ'].dropna().tolist())
    
    summary_data = []
    cert_achievers = 0
    
    for user in all_users:
        if str(user).strip() == "":
            continue
            
        stats = dm.calculate_user_stats(df_log, user)
        is_certified = stats['max_streak'] >= CERT_TARGET_STREAK
        
        if is_certified:
            cert_achievers += 1
            
        summary_data.append({
            'ชื่อ-นามสกุล': user,
            'สถานะเกียรติบัตร': '🏆 ผ่านเกณฑ์' if is_certified else '⏳ กำลังสะสม',
            'จำนวนครั้งที่ทำ': stats['log_data']['รวมของวันนั้น'].sum() if not stats['log_data'].empty else 0,
            'นาทีสะสมรวม': stats['total_minutes'],
            'จำนวนวันที่ทำ': stats['total_days'],
            'วันที่ทำต่อเนื่องสูงสุด': stats['max_streak']
        })
    
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric(label="📝 ลงทะเบียนทั้งหมด", value=f"{total_registered:,} คน")
    with c2:
        st.metric(label="👥 เริ่มปฏิบัติแล้ว", value=f"{admin_stats['total_users']:,} คน")
    with c3:
        st.metric(label="🌟 นาทีสะสมรวม", value=f"{admin_stats['total_minutes']:,} นาที")
    with c4:
        st.metric(label="🏆 ผ่านเกณฑ์แล้ว", value=f"{cert_achievers:,} คน")
        
    st.divider()
    
    st.subheader("📋 ตารางสรุปข้อมูลผู้เข้าร่วมทั้งหมด")
    if summary_data:
        df_summary = pd.DataFrame(summary_data)
        # จัดเรียงชื่อ ก-ฮ และรีเซ็ต Index เพื่อทำลำดับ
        df_summary = df_summary.sort_values(by='ชื่อ-นามสกุล', ascending=True).reset_index(drop=True)
        # แทรกคอลัมน์ ลำดับ ไว้ที่ตำแหน่งซ้ายสุด
        df_summary.insert(0, 'ลำดับ', range(1, len(df_summary) + 1))
        
        # ฟังก์ชันถมสีเฉพาะคนได้เกียรติบัตร
        def highlight_certified(val):
            if val == '🏆 ผ่านเกณฑ์':
                return 'color: #047857; font-weight: bold; background-color: #ecfdf5;'
            return ''
            
        # ฟังก์ชันไล่สเกลสีตามจำนวนวันที่ทำต่อเนื่อง (Streak)
        def style_streak(val):
            try:
                v = int(val)
                if v >= CERT_TARGET_STREAK: 
                    return 'background-color: #dcfce7; color: #166534; font-weight: bold;' # เขียวเข้ม
                elif v >= 20: 
                    return 'background-color: #ecfccb; color: #3f6212;' # เขียวสว่าง
                elif v >= 10: 
                    return 'background-color: #fefce8; color: #a16207;' # เหลือง
                elif v > 0: 
                    return 'background-color: #ffedd5; color: #9a3412;' # ส้ม
                else: 
                    return 'background-color: #fee2e2; color: #991b1b;' # แดง (0 วัน)
            except:
                return ''
            
        try:
            styled_summary = df_summary.style\
                .map(highlight_certified, subset=['สถานะเกียรติบัตร'])\
                .map(style_streak, subset=['วันที่ทำต่อเนื่องสูงสุด'])
        except AttributeError:
            styled_summary = df_summary.style\
                .applymap(highlight_certified, subset=['สถานะเกียรติบัตร'])\
                .applymap(style_streak, subset=['วันที่ทำต่อเนื่องสูงสุด'])
            
        st.dataframe(styled_summary, use_container_width=True, hide_index=True)
    else:
        st.info("ยังไม่มีข้อมูลการปฏิบัติในโครงการ")