def build_earn_notification_message(*, earned_points, purchase_amount, balance, expire_date, expiring_soon):
    lines = [
        "🎉 คุณได้รับคะแนนสะสมแล้ว!",
        f"ยอดซื้อ: {purchase_amount:,.2f} บาท",
        f"ได้รับ: +{earned_points} คะแนน",
        f"คะแนนสะสมปัจจุบัน: {balance:,} คะแนน",
    ]
    if expire_date:
        lines.append(f"คะแนนชุดนี้หมดอายุ: {expire_date.strftime('%d/%m/%Y')}")
    if expiring_soon > 0:
        lines.append(f"⚠️ มีคะแนน {expiring_soon:,} คะแนน ใกล้หมดอายุเร็วๆ นี้")
    lines.append("ตรวจสอบคะแนน/ประวัติได้ที่เมนูด้านล่าง")
    return "\n".join(lines)


def build_expiry_warning_message(*, balance, expiring_points, days):
    return (
        "⏰ แจ้งเตือนคะแนนใกล้หมดอายุ\n"
        f"คุณมีคะแนน {expiring_points:,} คะแนน ที่จะหมดอายุภายใน {days} วัน\n"
        f"คะแนนสะสมทั้งหมดของคุณ: {balance:,} คะแนน\n"
        "รีบใช้คะแนนก่อนหมดอายุนะครับ/คะ 🙏"
    )
