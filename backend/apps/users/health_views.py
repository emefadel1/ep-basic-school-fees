from decimal import Decimal
import shutil

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import caches
from django.db import connections
from django.db.models import Sum
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.models import AuditLog
from apps.fees.models import Distribution, FeeCollection, Session, StudentArrears
from apps.notifications.models import Notification
from apps.users.api.permissions import IsAuditViewer

def _check_database():
    try:
        with connections['default'].cursor() as cursor:
            cursor.execute('SELECT 1')
            cursor.fetchone()
        return dict(service='database', status='healthy', details='Database connection OK')
    except Exception as exc:
        return dict(service='database', status='unhealthy', details=f'Database check failed ({type(exc).__name__})')

def _check_cache():
    try:
        cache = caches['default']
        key = 'healthcheck:ping'
        value = timezone.now().isoformat()
        cache.set(key, value, 30)
        if cache.get(key) != value:
            raise RuntimeError('Cache round-trip failed')
        return dict(service='cache', status='healthy', details='Cache read/write OK')
    except Exception as exc:
        return dict(service='cache', status='degraded', details=f'Cache unavailable ({type(exc).__name__})')

def _check_disk():
    usage = shutil.disk_usage(settings.BASE_DIR)
    free_percent = round((usage.free / usage.total) * 100, 2)
    low_space = free_percent < 10
    return dict(
        service='disk',
        status='degraded' if low_space else 'healthy',
        details='Disk space checked',
        free_percent=free_percent,
        free_bytes=usage.free,
        total_bytes=usage.total,
    )

class HealthCheckView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        checks = dict(database=_check_database(), cache=_check_cache(), disk=_check_disk())
        statuses = [item['status'] for item in checks.values()]
        has_critical_failure = checks['database']['status'] == 'unhealthy'
        has_warning = 'degraded' in statuses or checks['cache']['status'] == 'unhealthy' or checks['disk']['status'] == 'unhealthy'
        overall_status = 'unhealthy' if has_critical_failure else 'degraded' if has_warning else 'healthy'
        http_status = status.HTTP_503_SERVICE_UNAVAILABLE if has_critical_failure else status.HTTP_200_OK
        payload = dict(
            status=overall_status,
            service='ep-basic-school-fees',
            environment='development' if settings.DEBUG else 'production',
            timestamp=timezone.now().isoformat(),
            checks=checks,
        )
        return Response(payload, status=http_status)

class MetricsView(APIView):
    permission_classes = [IsAuditViewer]

    def get(self, request):
        User = get_user_model()
        total_collected = FeeCollection.objects.aggregate(total=Sum('amount_paid')).get('total') or Decimal('0.00')
        payload = dict(
            timestamp=timezone.now().isoformat(),
            users=dict(total=User.objects.count(), active_staff=User.objects.filter(is_active_staff=True).count()),
            sessions=dict(total=Session.objects.count(), pending_approval=Session.objects.filter(status=Session.Status.PENDING_APPROVAL).count(), approved=Session.objects.filter(status=Session.Status.APPROVED).count(), locked=Session.objects.filter(status=Session.Status.LOCKED).count()),
            collections=dict(total=FeeCollection.objects.count(), total_amount=str(total_collected), arrears_open=StudentArrears.objects.exclude(status=StudentArrears.Status.PAID).count()),
            distributions=dict(total=Distribution.objects.count(), unpaid=Distribution.objects.filter(is_paid=False).count()),
            notifications=dict(unread=Notification.objects.filter(is_read=False).count()),
            audit=dict(total=AuditLog.objects.count()),
        )
        return Response(payload)

