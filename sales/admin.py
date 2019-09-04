from django.contrib import admin
from .models import InvoicesHeader, InvoicesDetail


@admin.register(InvoicesHeader)
class InvoicesHeaderAdmin(admin.ModelAdmin):
    list_display = ['id', 'customer_id', 'company_id']
    search_fields = ('customer_id', 'company_id',)


@admin.register(InvoicesDetail)
class InvoicesDetailAdmin(admin.ModelAdmin):
    list_display = ['id', 'product_id', 'price']
    search_fields = ('product_id', )
