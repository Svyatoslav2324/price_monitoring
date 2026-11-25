from django.contrib import admin

from .models import Tracking


@admin.register(Tracking)
class TrackingAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "product", "status", "check_interval", "target_price", "target_reached_at")
    list_filter = ("status", "check_interval")
    raw_id_fields = ("user", "product")
