from django.urls import path
from core.views import HealthView, MetricsView, DashboardSummaryView

urlpatterns = [
    path("health/", HealthView.as_view()),
    path("metrics/", MetricsView.as_view()),
    path("dashboard-summary/", DashboardSummaryView.as_view()),
]