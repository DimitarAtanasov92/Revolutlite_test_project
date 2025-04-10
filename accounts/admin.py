from django.contrib import admin
from .models import User

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'is_verified', 'needs_manual_review', 'confidence_score')
    list_filter = ('is_verified', 'needs_manual_review')
