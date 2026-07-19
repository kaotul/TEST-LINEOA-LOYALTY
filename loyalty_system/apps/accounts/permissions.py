from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def role_required(*roles):
    """
    Decorator: จำกัดให้เฉพาะ StaffUser ที่มี role อยู่ใน `roles` เข้าถึง view ได้
    ใช้งาน: @role_required("admin", "manager")
    """

    def decorator(view_func):
        @wraps(view_func)
        @login_required(login_url="pos:login")
        def _wrapped(request, *args, **kwargs):
            if request.user.role not in roles:
                raise PermissionDenied("คุณไม่มีสิทธิ์เข้าถึงหน้านี้")
            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator


def store_queryset_filter(user, queryset, store_field="store"):
    """
    Admin/Manager เห็นทุกสาขา, Staff เห็นเฉพาะสาขาตัวเอง
    """
    if user.is_manager_role or user.store_id is None:
        return queryset
    return queryset.filter(**{store_field: user.store_id})
