from django.conf.urls import url
from products.views import ProductList, ProductCategoryList, \
    ProductsStockList, ProductsTrackingList

urlpatterns = [
    url(r'^products/$', ProductList.as_view(), name='products'),
    url(r'^productCategories/$', ProductCategoryList.as_view(),
        name='productCategories'),
    url(r'^productsStocks/$', ProductsStockList.as_view(),
        name='productsStocks'),
    url(r'^productsTrackings/$', ProductsTrackingList.as_view(),
        name='productsTrackings')
]
