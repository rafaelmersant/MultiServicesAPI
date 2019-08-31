from django.conf.urls import url
from sales.views import InvoicesHeaderList, InvoicesDetailList

urlpatterns = [
    url(r'^invoicesHeaders/$', InvoicesHeaderList.as_view(),
        name='invoicesHeader'),
    url(r'^invoicesDetails/$', InvoicesDetailList.as_view(),
        name='invoicesDetail')
]
