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
