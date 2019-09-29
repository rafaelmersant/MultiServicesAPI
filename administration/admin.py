from django.contrib import admin
from .models import User, Customer, Company, FiscalGov


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['id', 'company_id', 'email', 'userRole',
                    'name', 'creationDate', 'createdByUser']
    list_editable = ('name',)
    search_fields = ('name', 'email',)


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'phoneNumber']
    search_fields = ('name',)


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['id', 'firstName', 'lastName']
    search_fields = ('firstName', 'lastName',)


@admin.register(FiscalGov)
class FiscalGovAdmin(admin.ModelAdmin):
    list_display = ['id', 'company_id', 'typeDoc', 'start', 'end']
    search_fields = ('company_id', 'typeDoc',)
