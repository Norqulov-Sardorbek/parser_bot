from django.urls import path
from razer.views.topup import JawalkerTopupView

urlpatterns = [
    path('start-task/', JawalkerTopupView.as_view(), name='start_task'),
]