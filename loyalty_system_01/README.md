# ระบบสะสมคะแนน (Loyalty Program) บน LINE OA

Full stack: **Django 6.0** + **PostgreSQL** + **Celery/Redis** + **LINE Messaging API / LIFF**

## สถาปัตยกรรม

```
customer มือถือ (LINE OA)          พนักงานหน้าร้าน (POS)
  │  Rich Menu ปุ่ม "คะแนนของฉัน"        │  เปิด /pos/ (login) กล้องสแกน QR
  ▼                                    ▼
LIFF page (templates/liff/points.html)   POS dashboard (templates/pos/dashboard.html)
  │  GET /customers/api/liff/me/            │  GET /pos/api/lookup/?token=
  │  (verify id_token กับ LINE ก่อนตอบ)      │  POST /pos/api/award/
  ▼                                    ▼
┌─────────────────────────────────────────────┐
│               Django (apps)                 │
│  customers  – Customer, QR token, LIFF API   │
│  points     – PointTransaction, PointBatch,  │
│               services.award/redeem/expire   │
│  pos        – staff dashboard + API          │
│  line_integration – webhook, push message,   │
│               rich menu setup                │
└─────────────────────────────────────────────┘
         │                         │
   PostgreSQL                Celery beat (ทุกชม./วัน)
                              -> expire_due_points
                              -> notify_expiring_points
                              -> push ผ่าน LINE Messaging API
```

## Mapping กับเงื่อนไขที่ต้องการ

| ข้อ | เงื่อนไข | ส่วนของโค้ด |
|---|---|---|
| 1 | ทุก 50 บาท = 1 คะแนน (ปรับได้) | `settings.BAHT_PER_POINT`, `points/services.py::calculate_points_from_amount` |
| 2 | สแกน QR ที่ POS แล้วกรอกยอด/กดให้คะแนน | `customers/models.py::Customer.qr_token`, `pos/views.py`, `templates/pos/dashboard.html` (html5-qrcode) |
| 3 | ดูคะแนนรวม/ประวัติ/วันหมดอายุผ่านปุ่ม Rich Menu | `line_integration` (rich menu + LIFF view), `customers/views.py::my_points_summary`, `templates/liff/points.html` |
| 4 | แจ้งเตือนยอดคะแนน + คะแนนใกล้หมดอายุ | `line_integration/client.py` (Flex message), `points/tasks.py` (Celery periodic) |

## กติกาแต้มหมดอายุ (FIFO)

แต้มแต่ละครั้งที่ได้รับจะถูกเก็บเป็น "ก้อน" (`PointBatch`) พร้อมวันหมดอายุของตัวเอง (ค่าเริ่มต้น 365 วันหลังได้รับ)
เวลาแลก/หักแต้ม ระบบจะตัดจากก้อนที่ **ใกล้หมดอายุที่สุดก่อน** (`points/services.py::redeem_points`)
ทำให้คำนวณ "คะแนนที่กำลังจะหมดอายุ" ได้แม่นยำในทุกช่วงเวลา ไม่ใช่แค่ยอดรวมเฉย ๆ

Celery beat มีสอง periodic task:
- `expire_due_points` (ทุกชั่วโมง) — ตัดก้อนที่หมดอายุแล้วออกจากยอด พร้อมบันทึกลงประวัติ
- `notify_expiring_points` (ทุกวัน) — เช็คว่าใครมีแต้มจะหมดอายุใน `EXPIRY_WARNING_DAYS` วัน แล้วส่ง LINE push

## การติดตั้ง (Dev)

```bash
python3.12 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env   # แล้วกรอกค่า LINE_CHANNEL_ACCESS_TOKEN, LINE_CHANNEL_SECRET, LIFF_ID ฯลฯ

# PostgreSQL: สร้าง database/user ให้ตรงกับ DATABASE_URL ใน .env
createdb loyalty_db

python manage.py migrate
python manage.py createsuperuser   # ใช้ล็อกอินเข้า /admin/ และผูก StaffProfile

# รัน dev server
python manage.py runserver

# แยกเทอร์มินัลรัน Celery (ต้องมี Redis รันอยู่)
celery -A config worker -l info
celery -A config beat -l info
```

### ผูกพนักงานเข้า POS

ใน `/admin/` สร้าง `StaffProfile` ผูกกับ User ที่ล็อกอินได้ — เฉพาะ user ที่มี `staff_profile` เท่านั้นที่กดให้คะแนนผ่าน `/pos/api/award/` ได้ (โค้ด check ใน `pos/views.py::award`)

### ตั้งค่า LINE

1. สร้าง Messaging API Channel ใน LINE Developers Console → คัดลอก Channel Access Token / Channel Secret ลง `.env`
2. ตั้ง Webhook URL เป็น `https://<your-domain>/line/webhook/`
3. สร้าง LIFF app (ขนาด Full) ชี้ไปที่ `https://<your-domain>/line/liff/points/` → คัดลอก LIFF ID / LIFF Channel ID ลง `.env`
4. เตรียมรูป Rich Menu (2500x843 px) แล้วรัน:
   ```bash
   python manage.py setup_richmenu --image richmenu.png
   ```
   คำสั่งนี้จะสร้างเมนู ตั้งปุ่ม "คะแนนของฉัน" ให้เปิด LIFF ที่สร้างไว้ และตั้งเป็นเมนู default ของทุกคนที่แชทกับ OA

## หมายเหตุด้านความปลอดภัย

- หน้า LIFF ยืนยันตัวลูกค้าด้วยการตรวจ `id_token` กับ LINE โดยตรง (`api.line.me/oauth2/v2.1/verify`) ก่อนตอบข้อมูลคะแนน ไม่เชื่อ `line_user_id` ที่ client ส่งมาตรง ๆ
- `qr_token` เป็น UUID แยกจาก `line_user_id` ป้องกันการเดา/ปลอมรหัสลูกค้า
- Webhook ตรวจ `X-Line-Signature` ทุกครั้งก่อนประมวลผล event
- Django 6.0 native CSP middleware เปิดใช้แล้วใน `settings.py` — ปรับ `SECURE_CSP` ให้ตรงโดเมนจริงก่อน deploy production
- Production ควรรันผ่าน `gunicorn` + Nginx/HTTPS, ปิด `DEBUG`, จำกัด `ALLOWED_HOSTS`

## โครงสร้างโปรเจกต์

```
config/            settings, urls, celery app
customers/         Customer model, QR image endpoint, LIFF summary API
points/            PointTransaction / PointBatch models, business logic (services.py), Celery tasks
pos/                หน้า staff dashboard + API สแกน/ให้คะแนน
line_integration/  webhook, LINE client (push/flex message), LIFF view, rich menu command
templates/pos/      หน้าสแกน QR ของพนักงาน
templates/liff/     หน้าคะแนนของลูกค้า (เปิดใน LINE ผ่าน LIFF)
```
