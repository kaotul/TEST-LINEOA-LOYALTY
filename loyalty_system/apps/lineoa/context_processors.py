from django.conf import settings


def liff_ids(request):
    return {"LIFF_ID": settings.LIFF_ID}
