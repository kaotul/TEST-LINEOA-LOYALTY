# ระบบสะสมคะแนน (Loyalty Program) บน LINE OA

Full-stack ด้วย **Django 6.x**, deploy ด้วย **Docker Compose**
(Postgres + Redis + Celery worker/beat + Nginx)

## สรุปฟีเจอร์ตามสเปค

| # | ข้อกำหนด | Implementation |
|---|---|---|
| 1 | สมาชิก login ผ่าน LINE OA | `apps/customers` — LIFF login, verify ID token กับ LINE Login API, เก็บใน session |
| 2 | ทุก 50 บาท = 1 แต้ม | `apps/loyalty/services.py::calculate_points` อัตราส่วนตั้งค่าได้ที่หน้า Settings (`PointsSetting`, singleton) |
| 3 | QR Code ต่อลูกค้า + POS สแกน/กรอกยอด | `apps/customers` สร้าง QR (`member_code`), `apps/pos` หน้าสแกนด้วยกล้อง (html5-qrcode) + กรอกยอดซื้อ |
| 4 | ลูกค้าดูคะแนน/ประวัติ/วันหมดอายุผ่าน Rich Menu | `apps/customers/templates/liff/*`, ปุ่ม Rich Menu เปิด LIFF app |
| 5 | แจ้งเตือนหลังได้แต้ม + แต้มใกล้หมดอายุ | `apps/loyalty/tasks.py` (Celery: push ทันทีหลังให้แต้ม + งานประจำวันแจ้งแต้มใกล้หมดอายุ) |
| 6 | หน้าบ้าน login local + RBAC | `apps/accounts` (`StaffUser.role`: admin/manager/staff), `apps/pos` |
| 7 | Django 6.x + Docker | `Dockerfile`, `docker-compose.yml` |

## โครงสร้างโปรเจกต์

```
config/            # settings, urls, celery app
apps/
  accounts/        # StaffUser (local login) + RBAC decorators
  customers/        # Store, Customer (LINE member), LIFF views/templates, QR
  loyalty/          # PointsSetting, PointTransaction (ledger), business logic, celery tasks
  lineoa/           # LINE Messaging/Login API client, webhook, rich menu setup command
  pos/              # หน้าร้าน/Dashboard: login, scan, award/redeem, reports, settings
```

### แนวคิดสำคัญของ ledger (ป้องกันแต้มเพี้ยน)

- ทุกการเปลี่ยนแปลงแต้ม (ได้/แลก/หมดอายุ/ปรับปรุง) บันทึกเป็น `PointTransaction` แถวใหม่เสมอ (append-only)
  ไม่มีการ UPDATE ยอดสะสมตรงๆ ที่ตัว Customer — ยอดคงเหลือคำนวณจาก `SUM(points)`
- แต้มที่ได้รับแต่ละครั้ง (`tx_type=earn`) มี `expire_date` และ `remaining_points` ของตัวเอง
  เมื่อแลก/หมดอายุ จะตัดจากก้อนที่ใกล้หมดอายุที่สุดก่อน (FIFO)
- Django admin ปิดการแก้ไข/ลบ `PointTransaction` โดยตรง ต้องผ่าน service (`award_points`/`redeem_points`) เท่านั้น

## เริ่มต้นใช้งาน (Docker)

```bash
cp .env.example .env
# แก้ .env ใส่ค่า LINE_CHANNEL_ID / LINE_CHANNEL_SECRET / LINE_CHANNEL_ACCESS_TOKEN / LIFF_ID
# และ DJANGO_SECRET_KEY, ALLOWED_HOSTS ให้เป็นโดเมนจริงของคุณ

docker compose up -d --build

# สร้างสาขาเริ่มต้น + ผู้ใช้ admin (admin / ChangeMe123! — เปลี่ยนรหัสทันที)
docker compose exec web python manage.py seed_initial_data

# (ถ้าต้องการ) สร้าง superuser เพิ่มเอง
docker compose exec web python manage.py createsuperuser
```

- Dashboard/POS: `http://your-domain/pos/login/`
- Django admin: `http://your-domain/admin/`
- LIFF app (เปิดจากใน LINE เท่านั้น): `https://liff.line.me/<LIFF_ID>`

## ตั้งค่าฝั่ง LINE Developers Console

1. สร้าง **Provider** และ **Messaging API channel** → ได้ `Channel ID`, `Channel secret`, และออก `Channel access token (long-lived)`
2. ในช่องเดียวกัน เปิดแท็บ **LIFF** → Add LIFF app
   - Endpoint URL: `https://your-domain/liff/`
   - Scope: `openid`, `profile`
   - บันทึกค่า `LIFF ID` ลงใน `.env`
3. ตั้งค่า Webhook URL ใน Messaging API: `https://your-domain/line/webhook/` แล้วเปิด "Use webhook"
4. ปิด auto-reply message ของ LINE OA official (ให้ระบบเราควบคุมข้อความเอง)
5. ตั้งค่า **Rich Menu** (ปุ่ม: คะแนนของฉัน / ประวัติ / QR รับแต้ม) — เตรียมรูป 2500x1686px แล้วรัน:
   ```bash
   docker compose exec web python manage.py setup_rich_menu --image /app/media/richmenu.png
   ```
   (ก็อปปี้รูปเข้า container ก่อน หรือ mount volume เพิ่มตามสะดวก)

## Role การเข้าถึงหน้าบ้าน (`apps/accounts`)

| Role | สิทธิ์ |
|---|---|
| `admin` | ทุกอย่าง รวมถึงตั้งค่าอัตราแต้ม/วันหมดอายุ |
| `manager` | ดูรายงานทุกสาขา, ให้/แลกแต้มได้ |
| `staff` | สแกน/ให้แต้ม/แลกแต้ม เฉพาะสาขาตัวเอง เห็นเฉพาะรายการสาขาตัวเองในแดชบอร์ด/รายงาน |

สร้างผู้ใช้พนักงานเพิ่มได้ที่ Django admin (`/admin/`) → StaffUser → กำหนด role และ store

## งานที่รันอัตโนมัติ (Celery beat)

- ทุกวัน 01:00 — `expire_due_points`: หักแต้มที่หมดอายุออกจากยอดคงเหลือ
- ทุกวัน 09:00 — `notify_expiring_points`: push แจ้งเตือนลูกค้าที่มีแต้มจะหมดอายุใน N วัน (ตั้งค่าได้)
- ทันทีหลังพนักงานกดให้แต้มที่หน้า POS — `notify_points_earned`: push สรุปยอดแต้ม + วันหมดอายุ

## หมายเหตุ / สิ่งที่ควรทำต่อก่อนใช้งานจริง

- เพิ่ม HTTPS (เช่น Let's Encrypt ผ่าน reverse proxy ด้านหน้า Nginx หรือใช้ Traefik/Caddy แทน) — LINE บังคับ LIFF/Webhook ต้องเป็น HTTPS
- เพิ่ม rate-limit / audit log สำหรับ endpoint `award_points`/`redeem_points`
- เพิ่มระบบ "แลกของรางวัล" (catalog) ถ้าต้องการมากกว่าการแลกแต้มเป็นตัวเลขอย่างเดียว
- ตั้งค่า backup ฐานข้อมูล Postgres ตามนโยบายองค์กร
