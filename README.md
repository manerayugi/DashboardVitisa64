# 🧘‍♂️ Dashboard วิทิสาสมาธิ 64

ระบบ Dashboard สำหรับติดตามและสรุปผลการปฏิบัติสมาธิในโครงการ "วิทิสาสมาธิ 49 ล้านนาที" พัฒนาด้วย [Streamlit](https://streamlit.io/) และดึงข้อมูลแบบ Real-time จาก Google Sheets

## ✨ ฟีเจอร์หลัก (Features)
* **ระบบ Login แบบ Single-key:** เข้าสู่ระบบด้วย "เบอร์โทรศัพท์" ที่ลงทะเบียนไว้ (รองรับสิทธิ์ Admin และ User ทั่วไป)
* **Personal Dashboard:** สรุปสถิติส่วนบุคคล (นาทีสะสมรวม, จำนวนวันที่ปฏิบัติ, และ Streak การทำต่อเนื่องสูงสุด)
* **Contribution Calendar:** ปฏิทินแสดงผลการปฏิบัติรายวัน ถมสีตามเกณฑ์ (เขียว=ครบ 3 ครั้ง, เหลือง=1-2 ครั้ง, แดง=ไม่ได้ทำ)
* **Admin View:** สิทธิ์ผู้ดูแลระบบสามารถดูภาพรวมของทั้งโครงการ, ตารางสรุปผลผู้เข้าร่วมทั้งหมด, และเลือกดูข้อมูลสถิติรายบุคคลได้
* **Data Integration:** ประมวลผลและดึงข้อมูลจาก Google Sheets (แบบ Export CSV) ทำให้ไม่กระทบกับสูตรคำนวณเดิมใน Sheet ต้นทาง

## 📊 โครงสร้างข้อมูล (Cleaned Data Schema)
โปรเจกต์นี้ดึงข้อมูลจาก Google Sheets จำนวน 2 ไฟล์ โดยข้อมูลจะต้องเป็น **หน้าที่ผ่านการ Clean และจัดกลุ่ม (Group by) มาแล้ว** (ไม่ใช่ Raw Data จาก Google Forms โดยตรง) เพื่อลดภาระการประมวลผลของแอปพลิเคชัน

**1. ฟอร์มลงทะเบียน (Registration Data)**
| ชื่อคอลัมน์ | คำอธิบาย |
| :--- | :--- |
| `ชื่อ_นามสกุล` | ชื่อและนามสกุลของผู้เข้าร่วมโครงการ (ไม่ต้องมีคำนำหน้า หรือเว้นวรรคให้ตรงกับฟอร์มบันทึกผล) |
| `เบอร์ติดต่อ` | เบอร์โทรศัพท์ 10 หลัก (ระบบหลังบ้านจะช่วยลบขีดและจัดการเลข 0 ด้านหน้าให้อัตโนมัติ) |

**2. ฟอร์มบันทึกผล (Log Data)**
*ใช้สูตร `QUERY` รวบข้อมูลให้เหลือเพียง 1 บรรทัดต่อ 1 วันต่อ 1 คน*
| ชื่อคอลัมน์ | คำอธิบาย |
| :--- | :--- |
| `เลือกชื่อผู้ปฏิบัติ` | ชื่อผู้เข้าร่วม (ใช้เป็น Key เชื่อมโยงกับฟอร์มลงทะเบียน) |
| `วันที่ปฏิบัติ` | วันที่บันทึกผล รูปแบบ `DD/MM/YYYY` (เช่น 01/06/2026) |
| `max คะแนนรอบ เช้า` | สถานะการทำสมาธิรอบเช้า (1 = ทำ, 0 หรือว่าง = ไม่ได้ทำ) |
| `max คะแนนรอบ กลางวัน` | สถานะการทำสมาธิรอบกลางวัน (1 = ทำ, 0 หรือว่าง = ไม่ได้ทำ) |
| `max คะแนนรอบ เย็น` | สถานะการทำสมาธิรอบเย็น (1 = ทำ, 0 หรือว่าง = ไม่ได้ทำ) |
| `รวมของวันนั้น` | ผลรวมจำนวนครั้งที่ทำสมาธิในวันนั้น (ค่า 0 ถึง 3) |

## 📸 ภาพตัวอย่างหน้าจอ (Screenshots)
*(หมายเหตุ: ข้อมูลในภาพตัวอย่างเป็นข้อมูลจำลองเพื่อการทดสอบระบบ ไม่มีข้อมูลส่วนบุคคลจริง)*

![หน้า Login](assets/screenshot_login.png)
*หน้าเข้าสู่ระบบด้วยเบอร์โทรศัพท์หรือรหัสผ่านแอดมิน*

![User Dashboard](assets/screenshot_user.png)
![User Dashboard](assets/screenshot_user2.png)
*หน้า Dashboard ส่วนตัว แสดงสถิติและปฏิทินการปฏิบัติธรรม*

![Admin Dashboard](assets/screenshot_admin.png)
*หน้า Admin Dashboard แสดงภาพรวมผู้เข้าร่วมทั้งโครงการ*

## 📁 โครงสร้างโปรเจกต์ (Project Structure)
```text
DashboardVitisa64/
├── .streamlit/             # (สร้างบนเครื่อง Local)
│   └── secrets.toml        # เก็บ URL ของ Google Sheets และเบอร์โทร Admin
├── assets/
│   └── logo.png            # โลโก้โครงการแสดงหน้า Login
├── app.py                  # ไฟล์หลัก (Main/Routing)
├── auth.py                 # ระบบจัดการการเข้าสู่ระบบ
├── components.py           # ระบบแสดงผลหน้าจอ (UI, ปฏิทิน, ตาราง)
├── data_manager.py         # โลจิกดึงข้อมูล Clean ข้อมูล และคำนวณสถิติ
├── requirements.txt        # รายชื่อไลบรารีที่จำเป็น (Streamlit, Pandas)
└── .gitignore              # ไฟล์ยกเว้นการอัปโหลดขึ้น Git
```

## 🚀 การติดตั้งและรันทดสอบในเครื่อง (Local Setup)

1. **Clone repository หรือเตรียมไฟล์โปรเจกต์**
   เปิด Terminal และเข้าไปที่โฟลเดอร์โปรเจกต์

2. **ติดตั้งไลบรารีที่จำเป็น**
   ```bash
   pip install -r requirements.txt
   ```

3. **ตั้งค่า Secrets**
   สร้างโฟลเดอร์ `.streamlit` และไฟล์ `secrets.toml` ไว้ข้างใน:
   ```bash
   mkdir -p .streamlit
   touch .streamlit/secrets.toml
   ```
   จากนั้นใส่ข้อมูล URL ของ Google Sheets (แบบ Export CSV) และเบอร์โทร Admin:
   ```toml
   [sheets]
   reg_url = "[https://docs.google.com/spreadsheets/d/e/.../pub?gid=...&single=true&output=csv](https://docs.google.com/spreadsheets/d/e/.../pub?gid=...&single=true&output=csv)"
   log_url = "[https://docs.google.com/spreadsheets/d/e/.../pub?gid=...&single=true&output=csv](https://docs.google.com/spreadsheets/d/e/.../pub?gid=...&single=true&output=csv)"

   [admin]
   phone_numbers = ["089xxxxxxx", "081xxxxxxx", "รหัสผ่านแอดมิน"]
   ```

4. **รันแอปพลิเคชัน**
   ```bash
   streamlit run app.py
   ```

## ☁️ การนำขึ้นระบบ (Deployment on Streamlit Community Cloud)

1. อัปโหลดโค้ดทั้งหมด (ยกเว้นโฟลเดอร์ `.streamlit/`) ขึ้น GitHub Repository ของคุณ
2. เข้าสู่ระบบ [Streamlit Community Cloud](https://share.streamlit.io/) และคลิก **"New app"**
3. เลือก Repository, Branch และใส่ `app.py` ในช่อง Main file path
4. ก่อนคลิก Deploy ให้กดที่ **"Advanced settings"** (หรือ App Settings > Secrets) 
5. คัดลอกเนื้อหาทั้งหมดจากไฟล์ `secrets.toml` ในเครื่องของคุณไปวางในกล่องข้อความ
6. คลิก **Deploy!**

## 🔒 ความปลอดภัย (Security Notes)
* ห้ามอัปโหลดโฟลเดอร์ `.streamlit/` ขึ้น GitHub เด็ดขาด (มีการตั้งค่าดักไว้ใน `.gitignore` แล้ว)
* การดึงข้อมูลจาก Google Sheets จะเป็นแบบอ่านอย่างเดียว (Read-only) ไม่มีสิทธิ์ในการเขียนทับข้อมูลเดิม