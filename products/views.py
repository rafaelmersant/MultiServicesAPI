""" Products views """

# Django
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404

# Django REST framework
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination

# Models
from .models import Product, ProductCategory, ProductsStock, \
    ProductsTracking, ProductsTrackingHeader, PurchaseOrder

# Serializers
from .serializers import ProductSerializer, ProductCategorySerializer, \
    ProductsStockSerializer, ProductsTrackingSerializer, \
    ProductsTrackingHeaderSerializer, PurchaseOrderSerializer, \
    ProductsProviderSerializer


class StandardResultsSetPagination(PageNumberPagination):
    """ Pagination for 10 records """

    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 10


class StandardResultsSetPaginationMedium(PageNumberPagination):
    """ Pagination for 20 records Level2 """

    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 20


class StandardResultsSetPaginationHigh(PageNumberPagination):
    """ Pagination for 50 records Level3 """

    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 50


class StandardResultsSetPaginationLevelHighest(PageNumberPagination):
    """ Pagination for 200 records Long """

    page_size = 200
    page_size_query_param = 'page_size'
    max_page_size = 200


class ProductList(generics.ListCreateAPIView):
    """ Product list """

    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    pagination_class = StandardResultsSetPaginationHigh
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['id', 'description',
                        'company', 'model', 'category_id', 'barcode']
    search_fields = ['description', 'barcode']

    def delete(self, request, pk=None):
        try:
            product = Product.objects.get(pk=pk)
            product.delete()
        except Product.DoesNotExists:
            return Response("Not Found", status=status.HTTP_404_NOT_FOUND)
        except Exception:
            return Response("Internal Error",
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response("deleted", status=status.HTTP_200_OK)

    def put(self, request, pk, format=None):
        product = Product.objects.get(pk=pk)
        serializer = ProductSerializer(product, data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProductCategoryList(generics.ListCreateAPIView):
    """ Product category list """

    queryset = ProductCategory.objects.all()
    serializer_class = ProductCategorySerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['id', 'description', 'company']

    def delete(self, request, pk=None):
        productCategory = ProductCategory.objects.get(pk=pk)
        productCategory.delete()
        return Response("deleted", status=status.HTTP_200_OK)

    def put(self, request, pk, format=None):
        productCategory = ProductCategory.objects.get(pk=pk)
        serializer = ProductCategorySerializer(
            productCategory, data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProductsStockList(generics.ListCreateAPIView):
    """ Product stock list """

    queryset = ProductsStock.objects.all()
    serializer_class = ProductsStockSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['id', 'company', 'product', 'modifiedUser']

    def delete(self, request, pk=None):
        productsStock = ProductsStock.objects.get(pk=pk)
        productsStock.delete()
        return Response("deleted", status=status.HTTP_200_OK)

    def put(self, request, pk, format=None):
        productsStock = ProductsStock.objects.get(pk=pk)
        serializer = ProductsStockSerializer(
            productsStock, data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProductsTrackingHeaderList(generics.ListCreateAPIView):
    """ Products tracking header list """

    queryset = ProductsTrackingHeader.objects.all()
    serializer_class = ProductsTrackingHeaderSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['id', 'company', 'provider',
                        'ncf', 'docDate', 'createdUser', 'paid', 'reference']

    def get_queryset(self):
        queryset = ProductsTrackingHeader.objects.all()

        provider_name = self.request.query_params.get('provider_name', None)
        if provider_name is not None:
            queryset = queryset.filter(
                provider__firstName__contains=provider_name)
        return queryset

    def delete(self, request, pk=None):
        productsTrackingHeader = ProductsTrackingHeader.objects.get(pk=pk)
        productsTrackingHeader.delete()
        return Response("deleted", status=status.HTTP_200_OK)

    def put(self, request, pk, format=None):
        productsTrackingHeader = ProductsTrackingHeader.objects.get(pk=pk)
        serializer = ProductsTrackingHeaderSerializer(
            productsTrackingHeader, data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProductsTrackingList(generics.ListCreateAPIView):
    """ Products tracking list detail """

    queryset = ProductsTracking.objects.all()
    serializer_class = ProductsTrackingSerializer
    pagination_class = StandardResultsSetPaginationMedium
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['id', 'company', 'concept', 'header',
                        'product', 'typeTracking', 'createdUser']

    def delete(self, request, pk=None):
        productsTracking = ProductsTracking.objects.get(pk=pk)
        productsTracking.delete()
        return Response("deleted", status=status.HTTP_200_OK)

    def put(self, request, pk, format=None):
        productsTracking = ProductsTracking.objects.get(pk=pk)
        serializer = ProductsTrackingSerializer(
            productsTracking, data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProductsTrackingListLong(generics.ListCreateAPIView):
    """ Products tracking list (with more items) """

    queryset = ProductsTracking.objects.all()
    serializer_class = ProductsTrackingSerializer
    pagination_class = StandardResultsSetPaginationLevelHighest
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['id', 'company', 'concept', 'header',
                        'product', 'typeTracking', 'createdUser']

    def delete(self, request, pk=None):
        productsTracking = ProductsTracking.objects.get(pk=pk)
        productsTracking.delete()
        return Response("deleted", status=status.HTTP_200_OK)

    def put(self, request, pk, format=None):
        productsTracking = ProductsTracking.objects.get(pk=pk)
        serializer = ProductsTrackingSerializer(
            productsTracking, data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PurchaseOrderList(generics.ListCreateAPIView):
    """ Purchase orders list """

    queryset = PurchaseOrder.objects.all()
    serializer_class = PurchaseOrderSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['id', 'company', 'product', 'quantity', 'pending']
    search_fields = ['product__description', ]

    def delete(self, request, pk=None):
        purchaseOrder = PurchaseOrder.objects.get(pk=pk)
        purchaseOrder.delete()
        return Response("deleted", status=status.HTTP_200_OK)

    def put(self, request, pk, format=None):
        purchaseOrder = PurchaseOrder.objects.get(pk=pk)
        serializer = PurchaseOrderSerializer(
            purchaseOrder, data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProductsProviderReport(generics.ListCreateAPIView):
    """ Products provider report """

    queryset = ProductsTracking.objects.all()
    serializer_class = ProductsProviderSerializer
    # pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['id', 'product', 'product_id']
    search_fields = ['product__description', ]

    def get_queryset(self):
        product_id = self.request.query_params.get
        (
            'product_id', None
        )

        if product_id is not None:
            queryset = ProductsTracking.objects.all().order_by("-creationDate")

        return queryset
