from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ECFCompanyViewSet, ECFSequenceViewSet


router = DefaultRouter()
router.register("electronic-invoices", ECFCompanyViewSet, basename="electronic-invoices")
router.register("electronic-invoice-sequences", ECFSequenceViewSet, basename="electronic-invoice-sequences")

urlpatterns = [path("", include(router.urls))]
