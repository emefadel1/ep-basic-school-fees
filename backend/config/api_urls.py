# config/api_urls.py

from django.urls import include, path
from rest_framework.routers import DefaultRouter
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.users.api.views import LoginView, LogoutView, ChangePasswordView
from rest_framework_simplejwt.views import TokenRefreshView
from apps.fees.api.views import SessionViewSet, CollectionViewSet, DistributionViewSet

router = DefaultRouter()
router.register(r"sessions", SessionViewSet, basename="session")
router.register(r"collections", CollectionViewSet, basename="collection")
router.register(r"distributions", DistributionViewSet, basename="distribution")

urlpatterns = [
    path("auth/login/", LoginView.as_view(), name="api-login"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="api-refresh"),
    path("auth/logout/", LogoutView.as_view(), name="api-logout"),
    path("auth/change-password/", ChangePasswordView.as_view(), name="api-change-password"),
    path("schema/", SpectacularAPIView.as_view(), name="api-schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="api-schema"), name="api-docs"),
    path("", include(router.urls)),
    path("reports/", include("apps.reports.api.urls")),
]