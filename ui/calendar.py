"""ปฏิทินรายเดือน: แสดงผลการปฏิบัติสมาธิรายวัน (ถมสีตามจำนวนรอบที่ทำได้) และผลบันทึกขององค์กร (ทำ/ไม่ทำ)"""
import calendar as calendar_lib
import datetime

import streamlit as st

# สีของแต่ละช่องวันในปฏิทิน: (พื้นหลัง, ขอบ, ตัวอักษร, ข้อความสถานะ)
DAY_STYLE_DONE = ("#ecfdf5", "#10b981", "#047857", "ครบ 3 ครั้ง")
DAY_STYLE_PARTIAL_TEMPLATE = ("#fefce8", "#eab308", "#a16207")  # ข้อความขึ้นกับจำนวนครั้งที่ทำ
DAY_STYLE_MISSED = ("#fef2f2", "#ef4444", "#b91c1c", "ไม่ได้ทำ")
DAY_STYLE_FUTURE = ("#ffffff", "#e5e7eb", "#d1d5db")  # วันในอนาคต ไม่ต้องมีสถานะ

DAY_STYLE_ORG_DONE = ("#ecfdf5", "#10b981", "#047857", "ทำแล้ว")
DAY_STYLE_ORG_MISSED = ("#fef2f2", "#ef4444", "#b91c1c", "ขาด")
DAY_STYLE_ORG_WEEKEND_OFF = ("#f9fafb", "#e5e7eb", "#9ca3af", "วันหยุด")  # เสาร์-อาทิตย์ที่ไม่ได้ทำ ไม่นับว่าขาด


def _get_day_style(count, current_date, today_date):
    """เลือกสีและข้อความของช่องวันตามจำนวนรอบที่ทำ (0-3) และว่าเป็นวันในอดีต/อนาคตหรือไม่"""
    if count >= 3:
        return DAY_STYLE_DONE
    if count in (1, 2):
        bg, border, text = DAY_STYLE_PARTIAL_TEMPLATE
        return bg, border, text, f"ทำ {int(count)} ครั้ง"
    if current_date <= today_date:
        return DAY_STYLE_MISSED
    return (*DAY_STYLE_FUTURE, "")


def _render_day_cell(col, day, count, current_date, today_date):
    bg_color, border_color, text_color, status_text = _get_day_style(count, current_date, today_date)

    if status_text:
        col.markdown(f"""
            <div style="position:relative; background-color:{bg_color}; border: 1px solid {border_color}; border-radius:8px; padding:6px; height:80px; display:flex; flex-direction:column; justify-content:center; align-items:center; box-shadow: 0 1px 2px rgba(0,0,0,0.05);">
                <span style="position:absolute; top:4px; left:6px; font-size:11px; color:#374151; font-weight:600;">{day}</span>
                <div style="text-align:center; line-height:1.2;">
                    <span style="font-size:11px; color:{text_color}; font-weight:700;">{status_text}</span><br>
                    <span style="font-size:10px; color:{text_color}; opacity: 0.8;">{int(count) * 5} นาที</span>
                </div>
            </div>
        """, unsafe_allow_html=True)
    else:
        col.markdown(f"""
            <div style="position:relative; background-color:#ffffff; border: 1px solid #e5e7eb; border-radius:8px; padding:6px; height:80px; display:flex; flex-direction:column; justify-content:center; align-items:center;">
                <span style="position:absolute; top:4px; left:6px; font-size:11px; color:#d1d5db; font-weight:500;">{day}</span>
            </div>
        """, unsafe_allow_html=True)


def render_calendar(user_log):
    """แสดงปฏิทินรายเดือนพร้อมปุ่มเลื่อนเดือนก่อนหน้า/ถัดไป (เก็บเดือน/ปีที่เลือกไว้ใน session_state)"""
    st.subheader("📅 ปฏิทินการปฏิบัติสมาธิ")
    latest_date = user_log['วันที่ปฏิบัติ'].max().date() if not user_log.empty else datetime.date.today()

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
        month_label = calendar_lib.month_name[st.session_state.cal_month]
        st.markdown(f"<h4 style='text-align:center; color:#374151; margin-top:5px;'>{month_label} {st.session_state.cal_year}</h4>", unsafe_allow_html=True)
    with head_col3:
        st.button("Next ▶️", on_click=next_month, use_container_width=True, key="next_cal")

    calendar_lib.setfirstweekday(calendar_lib.SUNDAY)
    cal = calendar_lib.monthcalendar(st.session_state.cal_year, st.session_state.cal_month)
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
                continue
            current_date = datetime.date(st.session_state.cal_year, st.session_state.cal_month, day)
            count = daily_stats.get(current_date, {}).get('Total_Sessions', 0)
            _render_day_cell(day_cols[idx], day, count, current_date, today_date)


def _get_org_day_style(is_active, current_date, today_date):
    """เลือกสีและข้อความของช่องวันสำหรับปฏิทินองค์กร (ทำ/ไม่ทำ) เสาร์-อาทิตย์ที่ไม่ได้ทำไม่ถือว่าขาด"""
    if is_active:
        return DAY_STYLE_ORG_DONE
    if current_date > today_date:
        return (*DAY_STYLE_FUTURE, "")
    if current_date.weekday() >= 5:  # 5 = เสาร์, 6 = อาทิตย์
        return DAY_STYLE_ORG_WEEKEND_OFF
    return DAY_STYLE_ORG_MISSED


def _render_org_day_cell(col, day, is_active, current_date, today_date):
    bg_color, border_color, text_color, status_text = _get_org_day_style(is_active, current_date, today_date)

    if status_text:
        col.markdown(f"""
            <div style="position:relative; background-color:{bg_color}; border: 1px solid {border_color}; border-radius:8px; padding:6px; height:64px; display:flex; flex-direction:column; justify-content:center; align-items:center; box-shadow: 0 1px 2px rgba(0,0,0,0.05);">
                <span style="position:absolute; top:4px; left:6px; font-size:11px; color:#374151; font-weight:600;">{day}</span>
                <span style="font-size:11px; color:{text_color}; font-weight:700;">{status_text}</span>
            </div>
        """, unsafe_allow_html=True)
    else:
        col.markdown(f"""
            <div style="position:relative; background-color:#ffffff; border: 1px solid #e5e7eb; border-radius:8px; padding:6px; height:64px; display:flex; flex-direction:column; justify-content:center; align-items:center;">
                <span style="position:absolute; top:4px; left:6px; font-size:11px; color:#d1d5db; font-weight:500;">{day}</span>
            </div>
        """, unsafe_allow_html=True)


def render_company_calendar(active_dates, key_prefix="org_cal"):
    """ปฏิทินรายเดือนของบริษัท 1 แห่ง (ทำ/ไม่ทำ) ใช้ session_state คนละคีย์กับ render_calendar
    เพื่อไม่ให้ชนกันตอนแท็บ Admin แสดงทั้งปฏิทินส่วนบุคคลและปฏิทินองค์กรพร้อมกัน
    """
    month_key, year_key = f'{key_prefix}_month', f'{key_prefix}_year'
    latest_date = max(active_dates) if active_dates else datetime.date.today()

    if month_key not in st.session_state:
        st.session_state[month_key] = latest_date.month
    if year_key not in st.session_state:
        st.session_state[year_key] = latest_date.year

    def prev_month():
        if st.session_state[month_key] == 1:
            st.session_state[month_key] = 12
            st.session_state[year_key] -= 1
        else:
            st.session_state[month_key] -= 1

    def next_month():
        if st.session_state[month_key] == 12:
            st.session_state[month_key] = 1
            st.session_state[year_key] += 1
        else:
            st.session_state[month_key] += 1

    head_col1, head_col2, head_col3 = st.columns([2, 4, 2])
    with head_col1:
        st.button("◀️ Prev", on_click=prev_month, use_container_width=True, key=f"{key_prefix}_prev")
    with head_col2:
        month_label = calendar_lib.month_name[st.session_state[month_key]]
        st.markdown(f"<h4 style='text-align:center; color:#374151; margin-top:5px;'>{month_label} {st.session_state[year_key]}</h4>", unsafe_allow_html=True)
    with head_col3:
        st.button("Next ▶️", on_click=next_month, use_container_width=True, key=f"{key_prefix}_next")

    calendar_lib.setfirstweekday(calendar_lib.SUNDAY)
    cal = calendar_lib.monthcalendar(st.session_state[year_key], st.session_state[month_key])
    days_of_week = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

    week_cols = st.columns(7)
    for idx, day_name in enumerate(days_of_week):
        week_cols[idx].markdown(f"<div style='text-align:center; font-weight:600; color:#9ca3af; font-size:12px; margin-bottom:8px;'>{day_name}</div>", unsafe_allow_html=True)

    today_date = datetime.date.today()
    for week in cal:
        day_cols = st.columns(7)
        for idx, day in enumerate(week):
            if day == 0:
                day_cols[idx].markdown("<div style='height:64px;'></div>", unsafe_allow_html=True)
                continue
            current_date = datetime.date(st.session_state[year_key], st.session_state[month_key], day)
            _render_org_day_cell(day_cols[idx], day, current_date in active_dates, current_date, today_date)
