"""หน้าสรุปผลรายบุคคล: การ์ดสถิติ, ปฏิทิน, และตารางประวัติการบันทึกผล"""
import streamlit as st

import config
import stats
from ui.calendar import render_calendar
from ui.styles import apply_styles, style_status, style_total_sessions


def _render_certification_banner(user_stats):
    """แถบแสดงสถานะเกียรติบัตร: ยินดีถ้าผ่านแล้ว, หรือ progress bar ไปสู่เป้าหมายถ้ายังไม่ผ่าน"""
    if user_stats['is_certified']:
        st.success(
            "🎉 **ขอแสดงความยินดี!** ท่านผ่านเกณฑ์รับเกียรติบัตรแล้ว "
            f"(ทำต่อเนื่องครบ {config.CERT_TARGET_STREAK} วัน และสะสมครบ {config.CERT_TARGET_MINUTES_IN_30D} นาทีสำเร็จ)",
            icon="🏆",
        )
        # โชว์ลูกโป่งครั้งเดียวต่อ session กันไม่ให้เด้งซ้ำทุกครั้งที่หน้าจอ rerun
        if 'balloons_shown' not in st.session_state:
            st.balloons()
            st.session_state['balloons_shown'] = True
        return

    st.markdown(f"**เป้าหมายเกียรติบัตร:** ทำต่อเนื่อง {config.CERT_TARGET_STREAK} วัน และสะสมเวลาให้ครบ {config.CERT_TARGET_MINUTES_IN_30D} นาที")
    if user_stats['max_streak_days'] < config.CERT_TARGET_STREAK:
        # ยังไม่ครบวันต่อเนื่อง -> โชว์ progress ของ streak ก่อน
        progress_val = min(user_stats['max_streak_days'] / config.CERT_TARGET_STREAK, 1.0)
        st.progress(progress_val)
        remaining_days = config.CERT_TARGET_STREAK - user_stats['max_streak_days']
        st.caption(f"🔥 ขาดความต่อเนื่องอีกเพียง **{remaining_days}** วัน")
    else:
        # ครบวันต่อเนื่องแล้ว -> โชว์ progress ของนาทีสะสมในช่วงนั้น
        progress_val = min(user_stats['cert_window_minutes'] / config.CERT_TARGET_MINUTES_IN_30D, 1.0)
        st.progress(progress_val)
        remaining_minutes = config.CERT_TARGET_MINUTES_IN_30D - user_stats['cert_window_minutes']
        st.caption(f"🔥 ทำต่อเนื่องครบ {config.CERT_TARGET_STREAK} วันแล้ว! ขาดเวลาสะสมอีกเพียง **{remaining_minutes}** นาที")


def _render_history_table(user_log):
    """ตารางประวัติการบันทึกผลรายวัน (เช้า/กลางวัน/เย็น/รวม) พร้อมสีไฮไลต์สถานะ"""
    if user_log.empty:
        st.info("ยังไม่มีข้อมูลการบันทึกผลสมาธิครับ")
        return

    df_display = user_log[['วันที่ปฏิบัติ', 'max คะแนนรอบ เช้า', 'max คะแนนรอบ กลางวัน', 'max คะแนนรอบ เย็น', 'รวมของวันนั้น']].copy()
    df_display = df_display.rename(columns={
        'max คะแนนรอบ เช้า': 'เช้า', 'max คะแนนรอบ กลางวัน': 'กลางวัน', 'max คะแนนรอบ เย็น': 'เย็น'
    })
    df_display['วันที่ปฏิบัติ'] = df_display['วันที่ปฏิบัติ'].dt.strftime('%d/%m/%Y')
    for col in ['เช้า', 'กลางวัน', 'เย็น']:
        df_display[col] = df_display[col].apply(lambda x: 'ทำแล้ว' if x == 1 else 'ไม่ได้ทำ')

    styled_df = apply_styles(df_display, [
        (style_status, ['เช้า', 'กลางวัน', 'เย็น']),
        (style_total_sessions, ['รวมของวันนั้น']),
    ])
    st.dataframe(styled_df, use_container_width=True, hide_index=True)


def user_dashboard(df_log, target_username):
    """หน้าแดชบอร์ดของผู้ปฏิบัติ 1 คน (ใช้ทั้งในแท็บส่วนตัว และตอน Admin เลือกดูรายคน)"""
    st.header(f"สถิติของ: {target_username}")
    user_stats = stats.calculate_user_stats(df_log, target_username)

    _render_certification_banner(user_stats)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric(label="📅 วันที่ปฏิบัติ (รวม)", value=f"{user_stats['total_days']:,} วัน")
    with c2:
        st.metric(label="⏱️ นาทีสะสม (รวม)", value=f"{user_stats['total_minutes']:,} นาที")
    with c3:
        st.metric(label="🔥 ทำต่อเนื่องสูงสุด", value=f"{user_stats['max_streak_days']:,} วัน", delta=user_stats['max_streak_period'], delta_color="off")
    with c4:
        st.metric(label="🌟 นาทีรวมช่วงต่อเนื่อง", value=f"{user_stats['minutes_in_max_streak']:,} นาที", delta="คิดจากรอบต่อเนื่องสูงสุด", delta_color="off")

    st.divider()
    render_calendar(user_stats['log_data'])

    st.subheader("📋 ประวัติการบันทึกผล")
    _render_history_table(user_stats['log_data'])
