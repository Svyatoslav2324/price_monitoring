from django.urls import path

from .views import ProductPreviewView

urlpatterns = [
    path("products/<int:nm_id>/", ProductPreviewView.as_view()),
]
