from django.urls import path

from .views import ProductDetailView, ProductHistoryView

urlpatterns = [
    path("<int:pk>/", ProductDetailView.as_view()),
    path("<int:pk>/history/", ProductHistoryView.as_view()),
]
