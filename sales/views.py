from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from django.db.models import Max
from rest_framework import generics, status
from rest_framework.response import Response
from .models import InvoicesHeader, InvoicesDetail
from .serializers import InvoicesHeaderSerializer, InvoicesDetailSerializer


class InvoicesHeaderList(generics.ListCreateAPIView):
    queryset = InvoicesHeader.objects.all()
    serializer_class = InvoicesHeaderSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['id', 'company', 'company_id', 'customer', 'sequence',
                        'customer_id', 'paymentMethod', 'ncf', 'createdUser']

    def delete(self, request, pk=None):
        try:
            invoiceHeader = InvoicesHeader.objects.get(pk=pk)
            invoiceHeader.delete()
        except InvoicesHeader.DoesNotExist:
            return Response("invoice header not found",
                            status=status.HTTP_404_NOT_FOUND)
        except:
            return Response("Internal Server Error",
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response("deleted", status=status.HTTP_200_OK)

    def put(self, request, pk, format=None):
        invoiceHeader = InvoicesHeader.objects.get(pk=pk)
        serializer = InvoicesHeaderSerializer(invoiceHeader, data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SequenceInvoice(generics.ListCreateAPIView):
    serializer_class = InvoicesHeaderSerializer

    def get(self, request, format=None, pk=None):
        try:
            # sequence = InvoicesHeader.objects.filter(company__id=pk)
            sequence = InvoicesHeader.objects.filter(
                company__id=pk).aggregate(Max('sequence'))

            nextSequence = \
                int(sequence["sequence__max"]
                    ) if sequence["sequence__max"] else 0

            return Response({"sequence": nextSequence + 1},
                            status=status.HTTP_200_OK)
        except:
            return Response("Bad request", status=status.HTTP_400_BAD_REQUEST)


class InvoicesDetailList(generics.ListCreateAPIView):
    queryset = InvoicesDetail.objects.all()
    serializer_class = InvoicesDetailSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['id', 'invoice', 'invoice_id',
                        'product', 'product_id', 'creationDate']

    def delete(self, request, pk=None):
        try:
            invoiceDetail = InvoicesDetail.objects.get(pk=pk)
            invoiceDetail.delete()
        except InvoicesDetail.DoesNotExist:
            return Response("invoice detail not found",
                            status=status.HTTP_404_NOT_FOUND)
        except:
            return Response("Internal Server Error",
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response("deleted", status=status.HTTP_200_OK)

    def put(self, request, pk, format=None):
        invoiceDetail = InvoicesDetail.objects.get(pk=pk)
        serializer = InvoicesDetailSerializer(invoiceDetail, data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
