from django.core.management.base import BaseCommand
from apps.accounts.models import StaffUser
from apps.customers.models import Store


class Command(BaseCommand):
    help = "สร้างข้อมูลตั้งต้น: สาขาเริ่มต้น + ผู้ใช้แอดมิน (สำหรับติดตั้งระบบครั้งแรก)"

    def handle(self, *args, **options):
        store, created = Store.objects.get_or_create(code="MAIN", defaults={"name": "สาขาหลัก"})
        if created:
            self.stdout.write(self.style.SUCCESS(f"สร้างสาขา: {store.name}"))

        if not StaffUser.objects.filter(username="admin").exists():
            StaffUser.objects.create_superuser(
                username="admin", password="ChangeMe123!", role=StaffUser.Role.ADMIN, store=store,
            )
            self.stdout.write(self.style.SUCCESS(
                "สร้างผู้ใช้แอดมิน: admin / ChangeMe123! (กรุณาเปลี่ยนรหัสผ่านทันที)"
            ))
        else:
            self.stdout.write("มีผู้ใช้ admin อยู่แล้ว ข้ามขั้นตอนนี้")
