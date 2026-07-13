"""ค่าคงที่ที่ใช้ร่วมกันทั้งโปรเจกต์"""
import datetime

# เกณฑ์รับเกียรติบัตร: ต้องทำต่อเนื่อง 30 วัน และสะสมนาทีให้ครบ 360 นาที
# ภายในช่วง 30 วันที่ต่อเนื่องนั้น (ดูตรรกะเต็มใน stats.calculate_user_stats)
CERT_TARGET_STREAK = 30
CERT_TARGET_MINUTES_IN_30D = 360

# Timezone ไทย (UTC+7) ใช้แสดงเวลา "อัปเดตล่าสุด" ใน sidebar ของ app.py
TZ_TH = datetime.timezone(datetime.timedelta(hours=7))

# เกณฑ์ผ่านสำหรับภาพรวมองค์กรภายนอก: ทำต่อเนื่อง 24 "วันทำการ"
# เสาร์-อาทิตย์ไม่ทำไม่ถือว่า streak ขาด แต่ถ้าทำก็นับรวมเป็นวันต่อเนื่องด้วย (ดูตรรกะเต็มใน org_stats.calculate_company_stats)
ORG_STREAK_TARGET = 24
