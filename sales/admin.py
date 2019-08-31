from django.contrib import admin
from .models import InvoicesHeader, InvoicesDetail


@admin.register(InvoicesHeader)
class InvoicesHeaderAdmin(admin.ModelAdmin):
    list_display = ['id', 'customerId', 'companyId']
    search_fields = ('customerId', 'companyId',)


@admin.register(InvoicesDetail)
class InvoicesDetailAdmin(admin.ModelAdmin):
    list_display = ['id', 'productId', 'price']
    search_fields = ('productId', )
