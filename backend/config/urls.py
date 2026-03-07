"""
Main URL Configuration for E.P Basic School Fee Management System.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from apps.users.views import home_view  # Import the home view for root URL

urlpatterns = [
    # Redirect root URL to the home view
    path('', home_view, name='home'),  # This points users to the home page

    # Admin panel
    path('admin/', admin.site.urls),
    
    # API v1
    path('api/v1/', include([
        path('auth/', include('apps.users.urls')),  # User authentication
        path('school/', include('apps.school.urls')),  # School-related views
        path('fees/', include('apps.fees.urls')),  # Fee management views
        path('reports/', include('apps.reports.urls')),  # Reporting views
        path('notifications/', include('apps.notifications.urls')),  # Notifications views
        path('audit/', include('apps.audit.urls')),  # Audit logs views
    ])),
    
    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    
    # Health check endpoint
    path('health/', include('apps.users.health_urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    
    # Include debug toolbar (only for development environment)
    import debug_toolbar
    urlpatterns = [
        path('__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns

# Custom admin site configuration
admin.site.site_header = 'E.P Basic School Administration'
admin.site.site_title = 'E.P Basic School Admin'
admin.site.index_title = 'Fee Management System'