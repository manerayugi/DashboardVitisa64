"""หน้าภาพรวมโครงการสำหรับ Admin: การ์ดสรุปภาพรวม + ตารางสถิติผู้เข้าร่วมทั้งหมด"""
import pandas as pd
import streamlit as st

import stats
from ui.styles import apply_styles, highlight_certified, style_streak_days


def _collect_all_usernames(df_reg, df_log):
    """รวมรายชื่อผู้ใช้จากทั้งฟอร์มลงทะเบียนและฟอร์มบันทึกผล (เผื่อมีคนทำ log ไว้แต่ยังไม่ได้ลงทะเบียน)"""
    all_users = set()
    if df_reg is not None and not df_reg.empty and 'ชื่อ_นามสกุล' in df_reg.columns:
        all_users.update(df_reg['ชื่อ_นามสกุล'].dropna().tolist())
    if df_log is not None and not df_log.empty and 'เลือกชื่อผู้ปฏิบัติ' in df_log.columns:
        all_users.update(df_log['เลือกชื่อผู้ปฏิบัติ'].dropna().tolist())
    return all_users


def _build_summary_table(df_log, all_users):
    """สร้างตารางสรุปสถิติรายบุคคล 1 แถวต่อ 1 คน สำหรับตาราง Admin"""
    summary_data = []
    cert_achievers = 0

    for user in all_users:
        if str(user).strip() == "":
            continue
        user_stats = stats.calculate_user_stats(df_log, user)
        if user_stats['is_certified']:
            cert_achievers += 1

        best_period = f"{user_stats['cert_window_start']} - {user_stats['cert_window_end']}" if user_stats['cert_window_start'] != "-" else "-"

        summary_data.append({
            'ชื่อ-นามสกุล': user,
            'สถานะเกียรติบัตร': '🏆 ผ่านเกณฑ์' if user_stats['is_certified'] else '⏳ กำลังสะสม',
            'นาทีสะสม (รวม)': user_stats['total_minutes'],
            'จำนวนวันที่ทำ (รวม)': user_stats['total_days'],
            'ต่อเนื่องสูงสุด (วัน)': user_stats['max_streak_days'],
            'นาทีสูงสุด (รอบ 30 วัน)': user_stats['cert_window_minutes'],
            'รอบ 30 วันที่ผ่านเกณฑ์': best_period,
            'ช่วงวันที่ทำต่อเนื่อง': user_stats['max_streak_period'],
            'นาทีรวมช่วงต่อเนื่อง': user_stats['minutes_in_max_streak'],
        })

    return summary_data, cert_achievers


def _render_summary_table(summary_data):
    df_summary = pd.DataFrame(summary_data)
    df_summary = df_summary.sort_values(by='ชื่อ-นามสกุล', ascending=True).reset_index(drop=True)
    df_summary.insert(0, 'ลำดับ', range(1, len(df_summary) + 1))

    styled_summary = apply_styles(df_summary, [
        (highlight_certified, ['สถานะเกียรติบัตร']),
        (style_streak_days, ['ต่อเนื่องสูงสุด (วัน)']),
    ])
    st.dataframe(styled_summary, use_container_width=True, hide_index=True)


def admin_dashboard(df_reg, df_log):
    """แดชบอร์ดภาพรวมโครงการ: จำนวนคนลงทะเบียน/เริ่มปฏิบัติ/ผ่านเกณฑ์ และตารางสถิติรายคนทั้งหมด"""
    st.header("👑 Admin Dashboard: ภาพรวมโครงการ")
    admin_stats = stats.calculate_admin_stats(df_log)
    total_registered = len(df_reg['ชื่อ_นามสกุล'].dropna().unique()) if not df_reg.empty else 0

    all_users = _collect_all_usernames(df_reg, df_log)
    summary_data, cert_achievers = _build_summary_table(df_log, all_users)

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
    st.subheader("📋 ตารางสรุปข้อมูลสถิติผู้เข้าร่วมโครงการ")

    if summary_data:
        _render_summary_table(summary_data)
    else:
        st.info("ยังไม่มีข้อมูลการปฏิบัติในโครงการ")
