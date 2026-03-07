from django.urls import path
from django.http import JsonResponse

def health_check(request):
    return JsonResponse({
        "status": "ok",
        "service": "EP Basic School Fee System"
    })

urlpatterns = [
    path('', health_check),
]
