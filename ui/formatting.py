"""ฟังก์ชันช่วยจัดรูปแบบตัวเลขสำหรับแสดงผล ใช้ร่วมกันระหว่าง user_view, org_view, admin_view"""


def format_days_since(days):
    """แปลงจำนวนวันที่ไม่ได้บันทึกผล (นับจากวันที่ปฏิบัติล่าสุด) เป็นข้อความแสดงผลบน metric card

    days เป็น None หมายถึงยังไม่เคยมีข้อมูลการปฏิบัติเลย
    """
    if days is None:
        return "-"
    return "วันนี้" if days == 0 else f"{days:,} วัน"


def as_nullable_int(series):
    """แปลงคอลัมน์เป็น pandas nullable Int64

    กันกรณีคอลัมน์ตัวเลข (เช่น days_since_*) มีค่า None ปนกับ int แล้ว pandas เปลี่ยนทั้งคอลัมน์เป็น
    float64 โดยอัตโนมัติ ทำให้ตารางโชว์ทศนิยมเกินจำเป็น (เช่น 1.000000) — Int64 แสดง None เป็น <NA> แทน
    """
    return series.astype('Int64')
