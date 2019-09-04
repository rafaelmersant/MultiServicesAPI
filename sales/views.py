from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from rest_framework import generics
from .models import InvoicesHeader, InvoicesDetail
from .serializers import InvoicesHeaderSerializer, InvoicesDetailSerializer


class InvoicesHeaderList(generics.ListCreateAPIView):
    queryset = InvoicesHeader.objects.all()
    serializer_class = InvoicesHeaderSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['id', 'company', 'company_id', 'customer',
                        'customer_id', 'paymentMethod', 'ncf', 'createdByUser']

    def get_object(self):
        data = InvoicesHeader.objects.all()

        obj = get_object_or_404(
            data,
            pk=self.kwargs['pk'],
        )
        return obj


class InvoicesDetailList(generics.ListCreateAPIView):
    queryset = InvoicesDetail.objects.all()
    serializer_class = InvoicesDetailSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['id', 'invoice', 'invoice_id',
                        'product', 'product_id', 'creationDate']

    def get_object(self):
        data = InvoicesDetail.objects.all()

        obj = get_object_or_404(
            data,
            pk=self.kwargs['pk'],
        )
        return obj
