from django.contrib import admin

from .models import Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("id", "marketplace", "external_id", "title", "current_price", "in_stock", "last_checked_at")
    list_filter = ("marketplace", "in_stock")
    search_fields = ("title", "external_id")
