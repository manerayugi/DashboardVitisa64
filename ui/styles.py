"""ฟังก์ชันจัดสีตารางข้อมูล (pandas Styler) ที่ใช้ร่วมกันระหว่าง user_view และ admin_view"""
import config


def style_status(val):
    """สีของช่อง เช้า/กลางวัน/เย็น ในตารางประวัติรายบุคคล"""
    if val == 'ทำแล้ว':
        return 'background-color: #dcfce7; color: #166534; font-weight: bold;'
    elif val == 'ไม่ได้ทำ':
        return 'background-color: #fee2e2; color: #991b1b;'
    return ''


def style_total_sessions(val):
    """สีของช่อง 'รวมของวันนั้น' ตามจำนวนรอบที่ทำได้ในวันนั้น (0-3)"""
    try:
        count = int(val)
        if count >= 3:
            return 'background-color: #ecfdf5; color: #047857; font-weight: bold;'
        elif count in [1, 2]:
            return 'background-color: #fefce8; color: #a16207; font-weight: bold;'
        else:
            return 'background-color: #fef2f2; color: #b91c1c; font-weight: bold;'
    except (ValueError, TypeError):
        return ''


def highlight_certified(val):
    """ไฮไลต์แถวที่มีสถานะ 'ผ่านเกณฑ์' ในตารางสรุปของ Admin"""
    return 'color: #047857; font-weight: bold; background-color: #ecfdf5;' if val == '🏆 ผ่านเกณฑ์' else ''


def make_streak_style(target):
    """สร้างฟังก์ชันไล่เฉดสีตามจำนวนวันต่อเนื่องสูงสุด เทียบกับเป้าหมายที่กำหนด (สัดส่วน ~33%/67% ของเป้าหมาย)

    ใช้ร่วมกันได้ทั้งเกียรติบัตรสมาธิรายบุคคล (config.CERT_TARGET_STREAK) และ streak องค์กร (config.ORG_STREAK_TARGET)
    """
    def _style(val):
        try:
            v = int(val)
            if v >= target:
                return 'background-color: #dcfce7; color: #166534; font-weight: bold;'
            elif v >= target * 0.67:
                return 'background-color: #ecfccb; color: #3f6212;'
            elif v >= target * 0.33:
                return 'background-color: #fefce8; color: #a16207;'
            elif v > 0:
                return 'background-color: #ffedd5; color: #9a3412;'
            else:
                return 'background-color: #fee2e2; color: #991b1b;'
        except (ValueError, TypeError):
            return ''
    return _style


style_streak_days = make_streak_style(config.CERT_TARGET_STREAK)


def apply_styles(df, style_map):
    """ช่วย apply .map()/.applymap() ให้รองรับทั้ง pandas เก่าและใหม่

    pandas >= 2.1 เปลี่ยนชื่อ Styler.applymap() เป็น Styler.map() แต่ยังรองรับ pandas เก่ากว่านั้น
    ที่ยังไม่มี .map() จึง fallback ไปเรียก .applymap() แทนเมื่อเจอ AttributeError

    style_map: list ของ (style_func, subset_columns)
    """
    styled = df.style
    try:
        for func, subset in style_map:
            styled = styled.map(func, subset=subset)
    except AttributeError:
        styled = df.style
        for func, subset in style_map:
            styled = styled.applymap(func, subset=subset)
    return styled
