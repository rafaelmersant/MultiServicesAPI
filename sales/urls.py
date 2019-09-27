from django.conf.urls import url
from sales.views import InvoicesHeaderList, InvoicesDetailList, \
    SequenceInvoice

urlpatterns = [
    url(r'^invoicesHeaders/$', InvoicesHeaderList.as_view(),
        name='invoicesHeader'),
    url(r'^invoicesHeaders/(?P<pk>[0-9]+)', InvoicesHeaderList.as_view(),
        name='invoicesHeader_byId'),

    url(r'^invoicesDetails/$', InvoicesDetailList.as_view(),
        name='invoicesDetail'),
    url(r'^invoicesDetails/(?P<pk>[0-9]+)', InvoicesDetailList.as_view(),
        name='invoicesDetail_byId'),

    url(r'^sequenceInvoice/(?P<pk>[0-9]+)', SequenceInvoice.as_view(),
        name='sequenceInvoice_byCompany'),

]
