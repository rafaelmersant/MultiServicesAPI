from django.conf.urls import url
from sales.views import InvoicesHeaderList, InvoicesDetailList

urlpatterns = [
    url(r'^invoicesHeaders/$', InvoicesHeaderList.as_view(),
        name='invoicesHeader'),
    url(r'^invoicesHeaders/(?P<pk>[0-9]+)', InvoicesHeaderList.as_view(),
        name='invoicesHeader_byId'),

    url(r'^invoicesDetails/$', InvoicesDetailList.as_view(),
        name='invoicesDetail'),
    url(r'^invoicesDetails/(?P<pk>[0-9]+)', InvoicesDetailList.as_view(),
        name='invoicesDetail_byId'),

]
