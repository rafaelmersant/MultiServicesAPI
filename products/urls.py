""" Products URLs. """

# Django
from django.urls import include, path

# Rest Framework
from rest_framework.routers import DefaultRouter

# Views
from . import views

router = DefaultRouter()
router.register('products', views.ProductViewSet)
router.register('updateData', views.UpdateDataViewSet)
router.register('productCategories', views.ProductCategoryViewSet)
router.register('productsStocks', views.ProductsStockViewSet)
router.register('productsTrackingsHeader', views.ProductsTrackingHeaderViewSet)
router.register('productsTrackings', views.ProductsTrackingViewSet)
router.register('productsTrackingsLong', views.ProductsTrackingListLong)
router.register('purchaseOrders', views.PurchaseOrderViewSet)
router.register('productsProviders', views.ProductsProviderReport)

urlpatterns = [
    path('', include(router.urls)),
]