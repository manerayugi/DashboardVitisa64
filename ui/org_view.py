"""แท็บภาพรวมองค์กรภายนอก (Admin only): สรุปยอดรวม + ตารางความต่อเนื่องรายบริษัท + รายละเอียดเมื่อเลือกบริษัท"""
import pandas as pd
import streamlit as st

import config
import org_stats
from ui.calendar import render_company_calendar
from ui.formatting import as_nullable_int, format_days_since
from ui.styles import apply_styles, make_streak_style


def _collect_all_companies(df_org_log, df_org_reg):
    """รวมรายชื่อบริษัทจากทั้งทะเบียนและฟอร์มบันทึกผล (เผื่อมีบริษัทที่บันทึกผลไว้แต่ตกทะเบียน หรือกลับกัน)"""
    companies = set()
    if not df_org_reg.empty:
        companies.update(df_org_reg['บริษัท'].dropna().tolist())
    if not df_org_log.empty:
        companies.update(df_org_log['บริษัท'].dropna().tolist())
    return sorted(c for c in companies if str(c).strip())


def _build_summary_table(df_org_log, df_org_reg):
    reg_by_company = df_org_reg.set_index('บริษัท')['จำนวนคนสมัคร'].to_dict() if not df_org_reg.empty else {}

    summary_data = []
    for company in _collect_all_companies(df_org_log, df_org_reg):
        company_stats = org_stats.calculate_company_stats(df_org_log, company, reg_by_company.get(company, 0))
        summary_data.append({
            'บริษัท': company,
            'สถานะ': '✅ ผ่านเกณฑ์' if company_stats['is_qualified'] else '⏳ กำลังสะสม',
            'คนสมัคร': company_stats['registered_people'],
            'วันที่ปฏิบัติ (รวม)': company_stats['total_days_done'],
            'นาทีสะสม (รวม)': company_stats['total_minutes'],
            'ต่อเนื่องสูงสุด (วัน)': company_stats['max_streak_days'],
            'ช่วงต่อเนื่องสูงสุด': company_stats['max_streak_period'],
            'วันที่ผ่านเกณฑ์ครั้งแรก': company_stats['first_qualified_date'],
            'วันที่ทำล่าสุด': company_stats['last_active_date'],
            'ไม่ได้ทำสมาธิมา (วัน)': company_stats['days_since_last_active'],
        })
    df_summary = pd.DataFrame(summary_data)
    if not df_summary.empty:
        df_summary['ไม่ได้ทำสมาธิมา (วัน)'] = as_nullable_int(df_summary['ไม่ได้ทำสมาธิมา (วัน)'])
    return df_summary


def _render_monthly_section(actual_df, forecast_df, actual_minutes_col='นาทีสะสม'):
    """แสดงตารางนาทีสะสมรายเดือน (จริง) + พยากรณ์เดือนถัดไป ใช้ร่วมกันทั้งภาพรวมองค์กรและรายบริษัท"""
    st.markdown("**📆 นาทีสะสมรายเดือน (จริง)**")
    if actual_df.empty:
        st.caption("ยังไม่มีข้อมูล")
    else:
        st.dataframe(actual_df, use_container_width=True, hide_index=True)

    if forecast_df is not None and not forecast_df.empty:
        st.markdown("**🔮 พยากรณ์เดือนถัดไป**")
        st.caption(
            "พยากรณ์ (run-rate) = อัตราการทำจริงเฉลี่ยที่ผ่านมา x วันทำการของเดือนนั้น (ใช้ค่านี้เป็นหลักสำหรับกรอกประมาณการ) "
            "· เต็มอัตรา (100%) = ค่าสูงสุดหากทำครบทุกวันทำการ ไว้เทียบเฉยๆ"
        )
        st.dataframe(forecast_df, use_container_width=True, hide_index=True)


def _render_company_detail(df_org_log, company_name, registered_people):
    company_stats = org_stats.calculate_company_stats(df_org_log, company_name, registered_people)
    st.subheader(f"📅 {company_name}")

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        st.metric("👥 คนสมัคร", f"{company_stats['registered_people']:,} คน")
    with c2:
        st.metric("📅 วันที่ปฏิบัติ (รวม)", f"{company_stats['total_days_done']:,} วัน")
    with c3:
        st.metric("🌟 นาทีสะสม (รวม)", f"{company_stats['total_minutes']:,} นาที")
    with c4:
        st.metric("🔥 ต่อเนื่องสูงสุด", f"{company_stats['max_streak_days']:,} วัน",
                   delta=company_stats['max_streak_period'], delta_color="off")
    with c5:
        status = "✅ ผ่านเกณฑ์แล้ว" if company_stats['is_qualified'] else "⏳ ยังไม่ผ่านเกณฑ์"
        st.metric("สถานะ", status)
    with c6:
        st.metric("⏳ ไม่ได้ทำสมาธิมา", format_days_since(company_stats['days_since_last_active']))

    active_dates = set(df_org_log[df_org_log['บริษัท'] == company_name]['วันที่ทำ'].dt.date)
    render_company_calendar(active_dates)

    st.divider()
    future_periods = org_stats.default_forecast_periods()
    monthly_actual = org_stats.calculate_monthly_actual(df_org_log, company_name, registered_people)
    monthly_actual = monthly_actual.drop(columns=['บริษัท']) if not monthly_actual.empty else monthly_actual
    monthly_forecast = org_stats.forecast_monthly(df_org_log, company_name, registered_people, future_periods)
    monthly_forecast = monthly_forecast.drop(columns=['บริษัท']) if not monthly_forecast.empty else monthly_forecast
    _render_monthly_section(monthly_actual, monthly_forecast)


def org_dashboard(df_org_log, df_org_reg):
    """แดชบอร์ดภาพรวมองค์กรภายนอก: เกณฑ์ทำต่อเนื่อง 24 วันทำการ (เสาร์-อาทิตย์ไม่ทำไม่ถือว่าขาด)"""
    st.header("🏢 ภาพรวมองค์กรภายนอก")

    if df_org_log.empty and df_org_reg.empty:
        st.info("ยังไม่มีข้อมูลจากองค์กรภายนอก")
        return

    org_summary = org_stats.calculate_org_summary(df_org_log, df_org_reg)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("🏢 บริษัทที่สมัคร", f"{org_summary['total_companies']:,} บริษัท")
    with c2:
        st.metric("👥 คนที่สมัครทั้งหมด", f"{org_summary['total_registered_people']:,} คน")
    with c3:
        st.metric("🌟 นาทีสะสมรวม (บันทึกจริง)", f"{org_summary['total_minutes']:,} นาที")
    with c4:
        st.metric("⏳ ไม่ได้ทำสมาธิมา (รวมทุกบริษัท)", format_days_since(org_summary['days_since_last_active']))

    st.divider()
    st.markdown("**📆 นาทีสะสมรายเดือน แยกตามบริษัท (จริง + พยากรณ์ run-rate)**")
    st.caption("เดือนที่ผ่านมาแล้วคือตัวเลขจริง เดือนที่ยังไม่ถึงเป็นค่าพยากรณ์แบบ run-rate (อัตราการทำจริงเฉลี่ย x วันทำการของเดือนนั้น) เดือน/บริษัทที่ไม่มีข้อมูลแสดงเป็น 0")
    future_periods = org_stats.default_forecast_periods()
    org_monthly_table = org_stats.calculate_org_monthly_table(df_org_log, df_org_reg, future_periods)
    if org_monthly_table.empty:
        st.caption("ยังไม่มีข้อมูล")
    else:
        st.dataframe(org_monthly_table, use_container_width=True, hide_index=True)

    st.divider()
    st.caption(f"เกณฑ์ความต่อเนื่อง: ทำต่อเนื่อง {config.ORG_STREAK_TARGET} วันทำการ (เสาร์-อาทิตย์ไม่ทำไม่ถือว่าขาด แต่ถ้าทำก็นับรวมด้วย)")

    df_summary = _build_summary_table(df_org_log, df_org_reg)
    styled_summary = apply_styles(df_summary, [
        (make_streak_style(config.ORG_STREAK_TARGET), ['ต่อเนื่องสูงสุด (วัน)']),
    ])

    st.caption("💡 คลิกเลือกแถวบริษัทในตาราง เพื่อดูรายละเอียดด้านล่าง")
    event = st.dataframe(
        styled_summary,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        column_config={
            'วันที่ผ่านเกณฑ์ครั้งแรก': st.column_config.DateColumn(format="DD/MM/YYYY"),
            'วันที่ทำล่าสุด': st.column_config.DateColumn(format="DD/MM/YYYY"),
        },
        key="org_summary_table",
    )

    st.divider()

    selected_rows = event.selection.rows if event and event.selection else []
    selected_row = df_summary.iloc[selected_rows[0]] if selected_rows else df_summary.iloc[0]
    _render_company_detail(df_org_log, selected_row['บริษัท'], selected_row['คนสมัคร'])
