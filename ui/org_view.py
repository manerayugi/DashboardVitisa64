"""แท็บภาพรวมองค์กรภายนอก (Admin only): สรุปยอดรวม + ตารางความต่อเนื่องรายบริษัท + รายละเอียดเมื่อเลือกบริษัท"""
import pandas as pd
import streamlit as st

import config
import org_stats
from ui.calendar import render_company_calendar
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
            'คนที่บันทึกจริง': company_stats['active_people'],
            'นาทีสะสม (รวม)': company_stats['total_minutes'],
            'ต่อเนื่องสูงสุด (วัน)': company_stats['max_streak_days'],
            'ช่วงต่อเนื่องสูงสุด': company_stats['max_streak_period'],
            'วันที่ผ่านเกณฑ์ครั้งแรก': company_stats['first_qualified_date'],
            'วันที่ทำล่าสุด': company_stats['last_active_date'],
        })
    return pd.DataFrame(summary_data)


def _render_company_detail(df_org_log, company_name, registered_people):
    company_stats = org_stats.calculate_company_stats(df_org_log, company_name, registered_people)
    st.subheader(f"📅 {company_name}")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("👥 คนสมัคร / บันทึกจริง", f"{company_stats['registered_people']:,} / {company_stats['active_people']:,} คน")
    with c2:
        st.metric("🌟 นาทีสะสม (รวม)", f"{company_stats['total_minutes']:,} นาที")
    with c3:
        st.metric("🔥 ต่อเนื่องสูงสุด", f"{company_stats['max_streak_days']:,} วัน",
                   delta=company_stats['max_streak_period'], delta_color="off")
    with c4:
        status = "✅ ผ่านเกณฑ์แล้ว" if company_stats['is_qualified'] else "⏳ ยังไม่ผ่านเกณฑ์"
        st.metric("สถานะ", status)

    active_dates = set(df_org_log[df_org_log['บริษัท'] == company_name]['วันที่ทำ'].dt.date)
    render_company_calendar(active_dates)


def org_dashboard(df_org_log, df_org_reg):
    """แดชบอร์ดภาพรวมองค์กรภายนอก: เกณฑ์ทำต่อเนื่อง 24 วันทำการ (เสาร์-อาทิตย์ไม่ทำไม่ถือว่าขาด)"""
    st.header("🏢 ภาพรวมองค์กรภายนอก")

    if df_org_log.empty and df_org_reg.empty:
        st.info("ยังไม่มีข้อมูลจากองค์กรภายนอก")
        return

    org_summary = org_stats.calculate_org_summary(df_org_log, df_org_reg)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("🏢 บริษัทที่สมัคร", f"{org_summary['total_companies']:,} บริษัท")
    with c2:
        st.metric("👥 คนที่สมัครทั้งหมด", f"{org_summary['total_registered_people']:,} คน")
    with c3:
        st.metric("🌟 นาทีสะสมรวม (บันทึกจริง)", f"{org_summary['total_minutes']:,} นาที")

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
