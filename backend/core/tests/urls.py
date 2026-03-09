from django.urls import path

from core.tests.views import ExceptionProbeView

urlpatterns = [
    path("exception-probe/<str:mode>/", ExceptionProbeView.as_view(), name="exception-probe"),
]
