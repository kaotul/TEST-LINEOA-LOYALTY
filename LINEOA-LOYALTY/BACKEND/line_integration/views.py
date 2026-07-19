from django.conf import settings
from django.shortcuts import render


def liff_points_page(request):
    """หน้าเว็บที่เปิดผ่าน LIFF เมื่อลูกค้ากดปุ่มบน Rich Menu (กติกาข้อ 3)"""
    return render(request, "liff/points.html", {"liff_id": settings.LIFF_ID})
