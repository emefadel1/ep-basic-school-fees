from django.core.management.base import BaseCommand

from apps.audit.services import run_retention_cleanup


class Command(BaseCommand):
    help = "Run notification and expired session retention cleanup."

    def handle(self, *args, **options):
        result = run_retention_cleanup()
        message = "Deleted {notifications_deleted} read notifications and {expired_sessions_deleted} expired auth sessions.".format(**result)
        self.stdout.write(self.style.SUCCESS(message))
