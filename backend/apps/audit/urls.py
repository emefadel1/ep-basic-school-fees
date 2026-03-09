from django.urls import path

from .views import AuditLogViewSet

app_name = "audit"

audit_list = AuditLogViewSet.as_view({"get": "list"})
audit_detail = AuditLogViewSet.as_view({"get": "retrieve"})

urlpatterns = [
    path("", audit_list, name="audit-log-list"),
    path("<int:pk>/", audit_detail, name="audit-log-detail"),
]
