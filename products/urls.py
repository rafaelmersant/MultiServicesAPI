from django.conf.urls import url
from products.views import ProductList, ProductCategoryList, \
    ProductsStockList, ProductsTrackingList, ProductsTrackingHeaderList, \
    PurchaseOrderList

urlpatterns = [
    url(r'^products/$', ProductList.as_view(), name='products'),
    url(r'^products/(?P<pk>[0-9]+)', ProductList.as_view(),
        name='product_byId'),

    url(r'^productCategories/$', ProductCategoryList.as_view(),
        name='productCategories'),
    url(r'^productCategories/(?P<pk>[0-9]+)', ProductCategoryList.as_view(),
        name='productCategories_byId'),

    url(r'^productsStocks/$', ProductsStockList.as_view(),
        name='productsStocks'),
    url(r'^productsStocks/(?P<pk>[0-9]+)', ProductsStockList.as_view(),
        name='productsStocks_byId'),

    url(r'^productsTrackingsHeader/$', ProductsTrackingHeaderList.as_view(),
        name='productsTrackingsHeader'),
    url(r'^productsTrackingsHeader/(?P<pk>[0-9]+)',
        ProductsTrackingHeaderList.as_view(),
        name='productsTrackingsHeader_byId'),

    url(r'^productsTrackings/$', ProductsTrackingList.as_view(),
        name='productsTrackings'),
    url(r'^productsTrackings/(?P<pk>[0-9]+)', ProductsTrackingList.as_view(),
        name='productsTrackings_byId'),

    url(r'^purchaseOrders/$', PurchaseOrderList.as_view(),
        name='purchaseOrders'),
    url(r'^purchaseOrders/(?P<pk>[0-9]+)', PurchaseOrderList.as_view(),
        name='purchaseOrders_byId')
]
