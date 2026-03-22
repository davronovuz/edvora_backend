from django.contrib import admin
from .models import Room


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ['number', 'name', 'room_type', 'capacity', 'status', 'floor']
    list_filter = ['room_type', 'status', 'floor']
    search_fields = ['name', 'number']
