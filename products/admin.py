from django.contrib import admin
from .models import Product, ProductCategory, ProductsStock, ProductsTracking


@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ['id', 'description']
    list_editable = ('description',)
    search_fields = ('description',)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['id', 'description']
    list_editable = ('description',)
    search_fields = ('description',)


@admin.register(ProductsTracking)
class ProductsTrackingAdmin(admin.ModelAdmin):
    list_display = ['id', 'product']
    search_fields = ('product',)


@admin.register(ProductsStock)
class ProductsStockAdmin(admin.ModelAdmin):
    list_display = ['id', 'product']
    search_fields = ('product',)
