from django.conf.urls import url
from administration.views import CompanyList, UserList, CustomerList, \
    FiscalGovList

urlpatterns = [
    url(r'^companies/$', CompanyList.as_view(), name='companies'),
    url(r'^companies/(?P<companyId>[\d]+)/$',
        CompanyList.as_view(), name='companiesById'),

    url(r'^users/$', UserList.as_view(), name='users'),
    url(r'^customers/$', CustomerList.as_view(), name='customers'),
    url(r'^fiscalGov/$', FiscalGovList.as_view(), name='customers'),
]
