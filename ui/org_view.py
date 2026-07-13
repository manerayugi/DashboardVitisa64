"""แท็บภาพรวมองค์กรภายนอก (Admin only): ตารางสรุปความต่อเนื่องรายบริษัท + รายละเอียดเมื่อเลือกบริษัท"""
import pandas as pd
import streamlit as st

import config
import org_stats
from ui.calendar import render_company_calendar
from ui.styles import apply_styles, make_streak_style


def _build_summary_table(df_org):
    companies = sorted(df_org['บริษัท'].dropna().unique().tolist())
    summary_data = []
    for company in companies:
        company_stats = org_stats.calculate_company_stats(df_org, company)
        summary_data.append({
            'บริษัท': company,
            'สถานะ': '✅ ผ่านเกณฑ์' if company_stats['is_qualified'] else '⏳ กำลังสะสม',
            'ต่อเนื่องสูงสุด (วัน)': company_stats['max_streak_days'],
            'ช่วงต่อเนื่องสูงสุด': company_stats['max_streak_period'],
            'วันที่ผ่านเกณฑ์ครั้งแรก': company_stats['first_qualified_date'],
            'วันที่ทำล่าสุด': company_stats['last_active_date'],
        })
    return pd.DataFrame(summary_data)


def _render_company_detail(df_org, company_name):
    company_stats = org_stats.calculate_company_stats(df_org, company_name)
    st.subheader(f"📅 {company_name}")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("🔥 ต่อเนื่องสูงสุด", f"{company_stats['max_streak_days']:,} วัน",
                   delta=company_stats['max_streak_period'], delta_color="off")
    with c2:
        st.metric("📆 จำนวนวันที่ทำ (รวม)", f"{company_stats['total_days_done']:,} วัน")
    with c3:
        status = "✅ ผ่านเกณฑ์แล้ว" if company_stats['is_qualified'] else "⏳ ยังไม่ผ่านเกณฑ์"
        st.metric("สถานะ", status)

    active_dates = set(df_org[df_org['บริษัท'] == company_name]['วันที่ทำ'].dt.date)
    render_company_calendar(active_dates)


def org_dashboard(df_org):
    """แดชบอร์ดภาพรวมองค์กรภายนอก: เกณฑ์ทำต่อเนื่อง 24 วันทำการ (เสาร์-อาทิตย์ไม่ทำไม่ถือว่าขาด)"""
    st.header("🏢 ภาพรวมองค์กรภายนอก")

    if df_org.empty:
        st.info("ยังไม่มีข้อมูลบันทึกผลจากองค์กรภายนอก")
        return

    st.caption(f"เกณฑ์: ทำต่อเนื่อง {config.ORG_STREAK_TARGET} วันทำการ (เสาร์-อาทิตย์ไม่ทำไม่ถือว่าขาด แต่ถ้าทำก็นับรวมด้วย)")

    df_summary = _build_summary_table(df_org)
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
    selected_company = df_summary.iloc[selected_rows[0]]['บริษัท'] if selected_rows else df_summary['บริษัท'].iloc[0]
    _render_company_detail(df_org, selected_company)
