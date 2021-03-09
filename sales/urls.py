""" Sales URLs. """

# Django
from django.conf.urls import url

# Views
from sales.views import InvoicesHeaderList, InvoicesDetailList, \
    InvoicesSequenceList, InvoicesHeaderListFull, InvoicesLeadsDetailList, \
    InvoicesLeadsHeaderList

urlpatterns = [
    url(r'^invoicesHeaders/$', InvoicesHeaderList.as_view(),
        name='invoicesHeader'),
    url(r'^invoicesHeaders/(?P<pk>[0-9]+)', InvoicesHeaderList.as_view(),
        name='invoicesHeader_byId'),

    url(r'^invoicesDetails/$', InvoicesDetailList.as_view(),
        name='invoicesDetail'),
    url(r'^invoicesDetails/(?P<pk>[0-9]+)', InvoicesDetailList.as_view(),
        name='invoicesDetail_byId'),

    url(r'^invoicesSequences/$', InvoicesSequenceList.as_view(),
        name='invoicesSequence'),
    url(r'^invoicesSequences/(?P<pk>[0-9]+)',
        InvoicesSequenceList.as_view(),
        name='invoicesSequence_byId'),

    url(r'^invoicesHeadersFull/$', InvoicesHeaderListFull.as_view(),
        name='invoicesHeaderFull'),

    url(r'^invoicesLeadHeader/$', InvoicesLeadsHeaderList.as_view(),
        name='invoicesLeadHeader'),
    url(r'^invoicesLeadHeader/(?P<id>[0-9]+)',
        InvoicesLeadsHeaderList.as_view(),
        name='invoicesLeadHeader_byId'),

    url(r'^invoicesLeadDetail/$', InvoicesLeadsDetailList.as_view(),
        name='invoicesLeadsDetail'),
    url(r'^invoicesLeadDetail/(?P<pk>[0-9]+)',
        InvoicesLeadsDetailList.as_view(),
        name='invoicesLeadsDetail_byId'),

]
