""" Sales views. """

# Django
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from django.db.models import Max

# Django REST framework
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination

# Models
from .models import InvoicesHeader, InvoicesDetail, InvoicesSequence, InvoicesLeadHeader, InvoicesLeadDetail

# Serializers
from .serializers import InvoicesHeaderSerializer, InvoicesDetailSerializer, InvoicesSequenceSerializer, \
    InvoicesLeadHeaderSerializer, InvoicesLeadDetailSerializer


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 10


class StandardResultsSetPagination2(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 50


class InvoicesHeaderList(generics.ListCreateAPIView):
    """ Invoices header list data. """

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
    """ Invoices details list related to an invoice header. """

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
    """ Invoices sequences list by companies.

    Here will be saved the sequence for invoice by companies.
    """

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
    """ Invoices header list full."""

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


class InvoicesLeadsHeaderList(generics.ListCreateAPIView):
    """ Invoices leads header list related to an invoice header. """

    queryset = InvoicesLeadHeader.objects.all()
    serializer_class = InvoicesLeadHeaderSerializer
    pagination_class = StandardResultsSetPagination2
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['id', 'invoice', 'invoice_id', 'creationDate']

    def delete(self, request, pk=None):
        try:
            InvoicesLeadHeader = InvoicesLeadHeader.objects.get(pk=pk)
            InvoicesLeadHeader.delete()
        except InvoicesLeadHeader.DoesNotExist:
            return Response("invoice lead header not found",
                            status=status.HTTP_404_NOT_FOUND)
        except:
            return Response("Internal Server Error",
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response("deleted", status=status.HTTP_200_OK)

    def put(self, request, pk, format=None):
        InvoicesLeadHeader = InvoicesLeadHeader.objects.get(pk=pk)
        serializer = InvoicesLeadHeaderSerializer(
            InvoicesLeadHeader, data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class InvoicesLeadsDetailList(generics.ListCreateAPIView):
    """ Invoices leads details list related to an invoice lead header. """

    queryset = InvoicesLeadDetail.objects.all()
    serializer_class = InvoicesLeadDetailSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['id', 'header', 'header_id',
                        'product', 'product_id', 'creationDate']

    def delete(self, request, pk=None):
        try:
            invoiceLeadDetail = InvoicesLeadDetail.objects.get(pk=pk)
            invoiceLeadDetail.delete()
        except invoiceLeadDetail.DoesNotExist:
            return Response("invoice lead detail not found",
                            status=status.HTTP_404_NOT_FOUND)
        except:
            return Response("Internal Server Error",
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response("deleted", status=status.HTTP_200_OK)

    def put(self, request, pk, format=None):
        invoiceLeadDetail = InvoicesLeadDetail.objects.get(pk=pk)
        serializer = InvoicesLeadDetailSerializer(
            invoiceLeadDetail, data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
