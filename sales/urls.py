""" Sales URLs. """


# Django
from django.urls import include, path

# Rest Framework
from rest_framework.routers import DefaultRouter

# Views
from . import views

router = DefaultRouter()
router.register('invoicesHeaders', views.InvoicesHeaderViewSet)
router.register('invoicesHeadersSearch', views.InvoicesHeaderSearchViewSet)
router.register('invoicesDetails', views.InvoicesDetailViewSet)
router.register('InvoicesDetailSimple', views.InvoicesDetailSimpleViewSet, basename="details")
router.register('invoicesDetailsReduced', views.InvoicesDetailReducedViewSet)
router.register('invoicesSequences', views.InvoicesSequenceViewSet)
router.register('invoicesHeadersFull', views.InvoicesHeaderListFull)
router.register('invoicesLeadHeader', views.InvoicesLeadsHeaderViewSet, basename="leadHeaders")
router.register('invoicesLeadDetail', views.InvoicesLeadsDetailViewSet)
router.register('quotationsHeaders', views.QuotationsHeaderViewSet)
router.register('quotationsDetails', views.QuotationsDetailViewSet)
router.register('invoicesCustomers', views.InvoicesCustomerViewSet, basename="invoicesCustomers")

urlpatterns = [
    path('', include(router.urls)),
    path('cancelInvoice/<int:invoice>', views.cancel_invoice)
]