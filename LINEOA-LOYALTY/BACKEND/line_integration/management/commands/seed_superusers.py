from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Seed two default superusers'

    def handle(self, *args, **options):
        User = get_user_model()

        superusers = [
            {
                'email': 'kaotul@hotmail.com',
                'username': 'kaotul',
                'password': 'ChangeMe123!',
            },
            {
                'email': 'admin@s-sofin.com',
                'username': 'admin',
                'password': 'ChangeMe123!',
            },
        ]

        for data in superusers:
            user, created = User.objects.get_or_create(
                email=data['email'],
                defaults={
                    'username': data['username'],
                    'is_staff': True,
                    'is_superuser': True,
                },
            )
            if created:
                user.set_password(data['password'])
                user.save()
                self.stdout.write(self.style.SUCCESS(
                    f"Created superuser {data['email']} with default password {data['password']}"
                ))
            else:
                updated = False
                if not user.is_staff:
                    user.is_staff = True
                    updated = True
                if not user.is_superuser:
                    user.is_superuser = True
                    updated = True
                if updated:
                    user.save()
                    self.stdout.write(self.style.WARNING(
                        f"Updated existing user {data['email']} to superuser"
                    ))
                else:
                    self.stdout.write(self.style.NOTICE(
                        f"Superuser {data['email']} already exists"
                    ))
