""" Products views """

# Django
from asyncio import mixins
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend

# Django REST framework
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.pagination import PageNumberPagination
from rest_framework.viewsets import ModelViewSet

# Models
from .models import (Product, ProductCategory, ProductsStock, ProductsTracking,
                     ProductsTrackingHeader, PurchaseOrder)
# Serializers
from .serializers import (ProductCategorySerializer, ProductSerializer,
                          ProductsProviderSerializer, ProductsStockSerializer,
                          ProductsTrackingHeaderSerializer,
                          ProductsTrackingSerializer, PurchaseOrderSerializer)


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 10


class StandardResultsSetPaginationMedium(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 20


class StandardResultsSetPaginationHigh(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 50


class StandardResultsSetPaginationLevelHighest(PageNumberPagination):
    page_size = 200
    page_size_query_param = 'page_size'
    max_page_size = 200


class ProductViewSet(ModelViewSet):
    queryset = Product.objects.select_related('company').select_related('category').select_related('stocks').all()
    serializer_class = ProductSerializer
    pagination_class = StandardResultsSetPaginationHigh
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['id', 'description', 'company', 'model', 'category_id', 'barcode']
    search_fields = ['description', 'barcode']


class ProductCategoryViewSet(ModelViewSet):
    queryset = ProductCategory.objects.select_related('company').all()
    serializer_class = ProductCategorySerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['id', 'description', 'company']


class ProductsStockViewSet(ModelViewSet):
    queryset = ProductsStock.objects.select_related('company').select_related('product').all()
    serializer_class = ProductsStockSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['company', 'product', 'modifiedUser']


class ProductsTrackingHeaderViewSet(ModelViewSet):
    queryset = ProductsTrackingHeader.objects.select_related('company').select_related('provider').all()
    serializer_class = ProductsTrackingHeaderSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['id', 'company', 'provider', 'ncf', 'docDate', 'createdUser', 'paid', 'reference']

    # def get_queryset(self):
    #     provider_name = self.request.query_params.get('provider_name', None)
    #     if provider_name is not None:
    #         queryset = queryset.filter(
    #             provider__firstName__contains=provider_name)
    #     return queryset


class ProductsTrackingViewSet(ModelViewSet):
    queryset = ProductsTracking.objects.select_related('company').prefetch_related('product').prefetch_related('header').all()
    serializer_class = ProductsTrackingSerializer
    pagination_class = StandardResultsSetPaginationMedium
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['id', 'company', 'concept', 'header',
                        'product', 'typeTracking', 'createdUser']


class ProductsTrackingListLong(ModelViewSet):
    queryset = ProductsTracking.objects.select_related('company').select_related('product').prefetch_related('header').all()
    serializer_class = ProductsTrackingSerializer
    pagination_class = StandardResultsSetPaginationLevelHighest
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['id', 'company', 'concept', 'header',
                        'product', 'typeTracking', 'createdUser']

   
class PurchaseOrderViewSet(ModelViewSet):
    queryset = PurchaseOrder.objects.select_related('company').select_related('product').all()
    serializer_class = PurchaseOrderSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['id', 'company', 'product', 'quantity', 'pending']
    search_fields = ['product__description', ]


class ProductsProviderReport(ModelViewSet):
    queryset = ProductsTracking.objects.prefetch_related('product').all()
    serializer_class = ProductsProviderSerializer
    pagination_class = StandardResultsSetPagination # remove
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
