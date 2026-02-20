from django.contrib import admin
from .models import TaskAccounts



@admin.register(TaskAccounts)
class TaskAccountsAdmin(admin.ModelAdmin):
    list_display = ('email', 'gold_balance', 'silver_balance')
    search_fields = ('email',)
    