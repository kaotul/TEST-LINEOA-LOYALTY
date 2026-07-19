import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Member",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("line_user_id", models.CharField(db_index=True, max_length=64, unique=True)),
                ("display_name", models.CharField(max_length=150)),
                ("picture_url", models.URLField(blank=True)),
                ("member_no", models.CharField(editable=False, max_length=20, unique=True)),
                ("first_name", models.CharField(max_length=100)),
                ("last_name", models.CharField(max_length=100)),
                (
                    "phone_number",
                    models.CharField(
                        max_length=10,
                        validators=[
                            django.core.validators.RegexValidator(
                                message="Enter a valid Thai mobile number, e.g. 0812345678.",
                                regex="^0\\d{8,9}$",
                            )
                        ],
                    ),
                ),
                ("email", models.EmailField(max_length=254)),
                ("date_of_birth", models.DateField()),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
    ]
