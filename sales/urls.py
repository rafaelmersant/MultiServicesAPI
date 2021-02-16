""" Sales URLs. """

# Django
from django.conf.urls import url

# Views
from sales.views import InvoicesHeaderList, InvoicesDetailList, \
    InvoicesSequenceList, InvoicesHeaderListFull, InvoicesLeadsDetailList

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

    url(r'^invoicesLeadsDetails/$', InvoicesLeadsDetailList.as_view(),
        name='invoicesLeadsDetail'),
    url(r'^invoicesLeadsDetails/(?P<pk>[0-9]+)',
        InvoicesLeadsDetailList.as_view(),
        name='invoicesLeadsDetail_byId'),

]
