from django.core.management.base import BaseCommand

from LINEOA.models import LINETemplate


class Command(BaseCommand):
    help = 'Seed example LINE templates for development and testing'

    def handle(self, *args, **options):
        templates = [
            {
                'code': 'WELCOME',
                'name': 'Welcome Message',
                'subject': 'Welcome to LINE OA',
                'HTML': '<p>Welcome to LINE OA</p>',
                'TEXT': 'Welcome to LINE OA',
                'note': 'Greeting template',
            },
            {
                'code': 'LINE_CANCEL',
                'name': 'Cancel Request',
                'subject': 'Cancel request received',
                'HTML': '<p>Your request has been cancelled.</p>',
                'TEXT': 'Your request has been cancelled.',
                'note': 'Cancellation flow',
            },
            {
                'code': 'LINE_TRIGGER',
                'name': 'Trigger Message',
                'subject': 'Trigger detected',
                'HTML': '<p>A trigger message was detected.</p>',
                'TEXT': 'A trigger message was detected.',
                'note': 'Trigger handling',
            },
            {
                'code': 'LINE_THANKYOU',
                'name': 'Thank You',
                'subject': 'Thank you',
                'HTML': '<p>Thank you for your message.</p>',
                'TEXT': 'Thank you for your message.',
                'note': 'General response',
            },
        ]

        created_count = 0
        for data in templates:
            obj, created = LINETemplate.objects.get_or_create(
                code=data['code'],
                defaults={
                    'name': data['name'],
                    'subject': data['subject'],
                    'HTML': data['HTML'],
                    'TEXT': data['TEXT'],
                    'note': data['note'],
                },
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"Created template {obj.code}"))
            else:
                self.stdout.write(self.style.NOTICE(f"Template {obj.code} already exists"))

        self.stdout.write(self.style.SUCCESS(f"Finished seeding LINETemplate examples ({created_count} created)"))
