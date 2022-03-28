# Django
from django.urls import include, path, re_path

# Rest Framework
from rest_framework.routers import DefaultRouter

# Views
from . import views

router = DefaultRouter()

router = DefaultRouter()
router.register('companies', views.CompanyViewSet)
router.register('users', views.UserViewSet)
router.register('customers', views.CustomerViewSet)
router.register('providers', views.ProviderViewSet)
router.register('fiscalGov', views.FiscalGovViewSet)

urlpatterns = [
    path('', include(router.urls)),
    re_path(r'^auth/login/$', views.UserLogin.as_view(), name='UserLogin'),
]

# urlpatterns = [
#     re_path(r'^companies/$', CompanyList.as_view(), name='companies'),
#     re_path(r'^companies/(?P<pk>[0-9]+)', CompanyList.as_view(),
#         name='company_byId'),

#     re_path(r'^users/$', UserList.as_view(), name='users'),
#     re_path(r'^users/(?P<pk>[0-9]+)', UserList.as_view(),
#         name='user_byId'),

#     re_path(r'^auth/login/$', UserLogin.as_view(),
#         name='UserLogin'),

#     re_path(r'^customers/$', CustomerList.as_view(), name='customers'),
#     re_path(r'^customers/(?P<pk>[0-9]+)',
#         CustomerList.as_view(), name='customer_byId'),

#     re_path(r'^providers/$', ProviderList.as_view(), name='providers'),
#     re_path(r'^providers/(?P<pk>[0-9]+)',
#         ProviderList.as_view(), name='provider_byId'),

#     re_path(r'^fiscalGov/$', FiscalGovList.as_view(), name='fiscalGov'),
#     re_path(r'^fiscalGov/(?P<pk>[0-9]+)',
#         FiscalGovList.as_view(), name='fiscalGov_byId'),
# ]
