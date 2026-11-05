""" Products URLs. """

# Django
from django.urls import include, path

# Rest Framework
from rest_framework.routers import DefaultRouter

# Views
from . import views

router = DefaultRouter()
router.register('products', views.ProductViewSet)
router.register('updateData', views.UpdateDataViewSet, basename="product-update-data")
router.register('productCategories', views.ProductCategoryViewSet, basename="product-categories")
router.register('productsStocks', views.ProductsStockViewSet, basename="products-stocks")
router.register('productsTrackingsHeader', views.ProductsTrackingHeaderViewSet, basename="products-tracking-header")
router.register('productsTrackings', views.ProductsTrackingViewSet, basename="products-tracking")
router.register('productsTrackingsLong', views.ProductsTrackingListLong, basename="products-tracking-long")
router.register('purchaseOrders', views.PurchaseOrderViewSet)
router.register('productsProviders', views.ProductsProviderReport)

urlpatterns = [
    path('', include(router.urls)),
]