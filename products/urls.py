""" Products URLs. """

# Django
from django.urls import include, path

# Rest Framework
from rest_framework.routers import DefaultRouter

# Views
from . import views

router = DefaultRouter()
router.register('products', views.ProductViewSet)
router.register('productCategories', views.ProductCategoryViewSet)

urlpatterns = [
    path('', include(router.urls)),
]

# urlpatterns = [
#     re_path(r'^products/$', ProductList.as_view, name='products'),
#     re_path(r'^products/(?P<pk>[0-9]+)', ProductList.as_view,
#         name='product_byId'),

    # re_path(r'^productCategories/$', ProductCategoryList.as_view(),
    #     name='productCategories'),
    # re_path(r'^productCategories/(?P<pk>[0-9]+)', ProductCategoryList.as_view(),
    #     name='productCategories_byId'),

    # re_path(r'^productsStocks/$', ProductsStockList.as_view(),
    #     name='productsStocks'),
    # re_path(r'^productsStocks/(?P<pk>[0-9]+)', ProductsStockList.as_view(),
    #     name='productsStocks_byId'),

    # re_path(r'^productsTrackingsHeader/$', ProductsTrackingHeaderList.as_view(),
    #     name='productsTrackingsHeader'),
    # re_path(r'^productsTrackingsHeader/(?P<pk>[0-9]+)',
    #     ProductsTrackingHeaderList.as_view(),
    #     name='productsTrackingsHeader_byId'),

    # re_path(r'^productsTrackings/$', ProductsTrackingList.as_view(),
    #     name='productsTrackings'),
    # re_path(r'^productsTrackings/(?P<pk>[0-9]+)', ProductsTrackingList.as_view(),
    #     name='productsTrackings_byId'),

    # re_path(r'^productsTrackingsLong/$', ProductsTrackingListLong.as_view(),
    #     name='productsTrackingsLong'),
    # re_path(r'^productsTrackingsLong/(?P<pk>[0-9]+)',
    #     ProductsTrackingListLong.as_view(),
    #     name='productsTrackingsLong_byId'),

    # re_path(r'^purchaseOrders/$', PurchaseOrderList.as_view(),
    #     name='purchaseOrders'),
    # re_path(r'^purchaseOrders/(?P<pk>[0-9]+)', PurchaseOrderList.as_view(),
    #     name='purchaseOrders_byId'),

    # re_path(r'^productsProviders/$', ProductsProviderReport.as_view(),
    #     name='products_providers_report')
# ]
