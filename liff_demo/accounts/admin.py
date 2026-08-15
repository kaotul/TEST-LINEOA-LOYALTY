from django.contrib import admin
from .models import LineProfile


@admin.register(LineProfile)
class LineProfileAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'line_user_id', 'user', 'email', 'created_at')
    search_fields = ('display_name', 'line_user_id', 'email', 'user__username')
