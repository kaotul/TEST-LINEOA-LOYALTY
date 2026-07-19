from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone

phone_validator = RegexValidator(
    regex=r"^0\d{8,9}$",
    message="Enter a valid Thai mobile number, e.g. 0812345678.",
)


class Member(models.Model):
    """
    A registered LINE OA member.

    `line_user_id` is the immutable, globally-unique id LINE assigns to a
    user for a given channel (the "sub" claim of the ID token). It is the
    only thing we ever trust to identify who is calling the API -- it is
    NOT taken at face value from the client; see members.line_client.verify_id_token.
    """

    # --- Identity from LINE -------------------------------------------------
    line_user_id = models.CharField(max_length=64, unique=True, db_index=True)
    display_name = models.CharField(max_length=150)
    picture_url = models.URLField(blank=True)

    # --- Member-submitted profile -------------------------------------
    member_no = models.CharField(max_length=20, unique=True, editable=False)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=10, validators=[phone_validator])
    email = models.EmailField()
    date_of_birth = models.DateField()

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.member_no} · {self.first_name} {self.last_name}"

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)
        if is_new and not self.member_no:
            # Assign a stable, human-readable member number once we have a pk.
            # e.g. M-2026-000042
            year = timezone.localdate().year
            self.member_no = f"M-{year}-{self.pk:06d}"
            super().save(update_fields=["member_no"])
