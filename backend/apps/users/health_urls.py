from django.urls import path

from apps.users.health_views import HealthCheckView, MetricsView

urlpatterns = [
    path('health/', HealthCheckView.as_view(), name='health-check'),
    path('metrics/', MetricsView.as_view(), name='metrics'),
]
