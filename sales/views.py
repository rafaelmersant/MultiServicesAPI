from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.shortcuts import get_object_or_404
from django.db.models import Max
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from .models import InvoicesHeader, InvoicesDetail, InvoicesSequence
from .serializers import InvoicesHeaderSerializer, InvoicesDetailSerializer, \
    InvoicesSequenceSerializer


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 10


class InvoicesHeaderList(generics.ListCreateAPIView):
    queryset = InvoicesHeader.objects.all()
    serializer_class = InvoicesHeaderSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
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


class InvoicesSequenceList(generics.ListCreateAPIView):
    queryset = InvoicesSequence.objects.all()
    serializer_class = InvoicesSequenceSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['id', 'company', 'company_id', 'sequence',
                        'createdUser']

    def delete(self, request, pk=None):
        try:
            invoiceSequence = InvoicesSequence.objects.get(pk=pk)
            invoiceSequence.delete()
        except InvoicesSequence.DoesNotExist:
            return Response("invoice sequence not found",
                            status=status.HTTP_404_NOT_FOUND)
        except:
            return Response("Internal Server Error",
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response("deleted", status=status.HTTP_200_OK)

    def put(self, request, pk, format=None):
        invoiceSequence = InvoicesSequence.objects.get(pk=pk)
        serializer = InvoicesSequenceSerializer(
            invoiceSequence, data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class InvoicesHeaderListFull(generics.ListCreateAPIView):
    queryset = InvoicesHeader.objects.all()
    serializer_class = InvoicesHeaderSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
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
