from django.conf.urls import url
from administration.views import CompanyList, UserList, CustomerList, \
    FiscalGovList, UserLogin

urlpatterns = [
    url(r'^companies/$', CompanyList.as_view(), name='companies'),
    url(r'^companies/(?P<pk>[0-9]+)', CompanyList.as_view(),
        name='company_byId'),

    url(r'^users/$', UserList.as_view(), name='users'),
    url(r'^users/(?P<pk>[0-9]+)', UserList.as_view(),
        name='user_byId'),

    url(r'^login/(?P<email>.*)/(?P<password>.*)', UserLogin.as_view(),
        name='UserLogin'),
    # url(r'^login/(?P<email>[\w-]+)/(?P<password>[\w-]+)', UserLogin.as_view(),
    #     name='UserLogin'),

    url(r'^customers/$', CustomerList.as_view(), name='customers'),
    url(r'^customers/(?P<pk>[0-9]+)',
        CustomerList.as_view(), name='customer_byId'),

    url(r'^fiscalGov/$', FiscalGovList.as_view(), name='fiscalGov'),
    url(r'^fiscalGov/(?P<pk>[0-9]+)',
        FiscalGovList.as_view(), name='fiscalGov_byId'),
]
