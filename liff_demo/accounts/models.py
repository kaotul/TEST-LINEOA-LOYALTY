from django.conf import settings
from django.db import models


class LineProfile(models.Model):
    """Extra LINE-specific data attached to a normal Django auth User."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='line_profile',
    )
    line_user_id = models.CharField(max_length=64, unique=True, db_index=True)  # the "sub" claim
    display_name = models.CharField(max_length=150, blank=True)
    picture_url = models.URLField(blank=True)
    email = models.EmailField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.display_name} ({self.line_user_id})'
