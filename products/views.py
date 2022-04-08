""" Products views """

# Django
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend

# Django REST framework
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.viewsets import ModelViewSet

# Models
from .models import (Product, ProductCategory, ProductsStock, ProductsTracking,
                     ProductsTrackingHeader, PurchaseOrder)
# Serializers
from .serializers import (ProductCategoryReducedSerializer, ProductCategorySerializer, ProductReducedSerializer, ProductSerializer, ProductsProviderSerializer,  
                          ProductsStockReducedSerializer, ProductsStockSerializer, ProductsTrackingHeaderReducedSerializer, ProductsTrackingHeaderSerializer, ProductsTrackingReducedSerializer,
                          ProductsTrackingSerializer, PurchaseOrderReducedSerializer, PurchaseOrderSerializer)

from MultiServices.paginations import (StandardResultsSetPagination, StandardResultsSetPaginationHigh,
                                    StandardResultsSetPaginationLevelHighest, StandardResultsSetPaginationMedium)


class ProductViewSet(ModelViewSet):
    queryset = Product.objects.select_related('company').select_related('category').select_related('stocks').all()
    pagination_class = StandardResultsSetPaginationHigh
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['id', 'description', 'company', 'model', 'category_id', 'barcode']
    search_fields = ['description', 'barcode']

    def get_serializer_class(self):
        # products = Product.objects.all()
        # for prod in products:
        #     tracking = ProductsTracking.objects.filter(product_id=prod.id, typeTracking='S').count()
        #     prod.ocurrences = tracking
        #     prod.save()

        if self.request.method == 'PUT':
            return ProductReducedSerializer
        return ProductSerializer


class ProductCategoryViewSet(ModelViewSet):
    queryset = ProductCategory.objects.select_related('company').all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['id', 'description', 'company']

    def get_serializer_class(self):
        if self.request.method == 'PUT':
            return ProductCategoryReducedSerializer
        return ProductCategorySerializer


class ProductsStockViewSet(ModelViewSet):
    http_method_names = ['get', 'post', 'put']
    queryset = ProductsStock.objects.select_related('company').select_related('product').all()
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['company', 'product', 'modifiedUser']

    def get_serializer_class(self):
        if self.request.method == 'PUT':
            return ProductsStockReducedSerializer
        return ProductsStockSerializer


class ProductsTrackingHeaderViewSet(ModelViewSet):
    http_method_names = ['get', 'post', 'put']
    queryset = ProductsTrackingHeader.objects.select_related('company').select_related('provider').all()
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['id', 'company', 'provider', 'ncf', 'docDate', 'createdUser', 'paid', 'reference']

    def get_serializer_class(self):
        if self.request.method == 'PUT':
            return ProductsTrackingHeaderReducedSerializer
        return ProductsTrackingHeaderSerializer

    # def get_queryset(self):
    #     provider_name = self.request.query_params.get('provider_name', None)
    #     if provider_name is not None:
    #         queryset = queryset.filter(
    #             provider__firstName__contains=provider_name)
    #     return queryset


class ProductsTrackingViewSet(ModelViewSet):
    http_method_names = ['get', 'post', 'put']
    queryset = ProductsTracking.objects.select_related('company').prefetch_related('product').prefetch_related('header').all()
    pagination_class = StandardResultsSetPaginationMedium
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['id', 'company', 'concept', 'header', 'product', 'typeTracking', 'createdUser']

    def get_serializer_class(self):
        if self.request.method == 'PUT':
            return ProductsTrackingReducedSerializer
        return ProductsTrackingSerializer


class ProductsTrackingListLong(ModelViewSet):
    http_method_names = ['get']
    queryset = ProductsTracking.objects.select_related('company').select_related('product').prefetch_related('header').all()
    serializer_class = ProductsTrackingSerializer
    pagination_class = StandardResultsSetPaginationLevelHighest
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['id', 'company', 'concept', 'header', 'product', 'typeTracking', 'createdUser']

   
class PurchaseOrderViewSet(ModelViewSet):
    http_method_names = ['get', 'post', 'put']
    queryset = PurchaseOrder.objects.select_related('company').select_related('product').all()
    serializer_class = PurchaseOrderSerializer
    pagination_class = StandardResultsSetPaginationMedium
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['id', 'company', 'product', 'quantity', 'pending']
    search_fields = ['product__description', ]

    def get_serializer_class(self):
        if self.request.method == 'PUT':
            return PurchaseOrderReducedSerializer
        return PurchaseOrderSerializer


class ProductsProviderReport(ModelViewSet):
    queryset = ProductsTracking.objects.select_related('company').select_related('product').select_related('header').all()
    serializer_class = ProductsProviderSerializer
    filter_backends = [SearchFilter, ]
    filterset_fields = ['id', 'product', 'product_id']
    
    def get_queryset(self):
        product_id = self.request.query_params.get('product_id', None)

        if product_id is not None:
            query = """
                    select t.id, t.product_id, p.id provider_id, p.firstName,
                        t.price, h.creationDate
                            from products_productsTracking t
                            inner join products_productsTrackingHeader h on h.id = t.header_id 
                            inner join administration_provider p on p.id = h.provider_id
                            where t.typeTracking = 'E' and t.product_id = {product_id}
                            order by h.creationDate desc
                    """.replace("{product_id}", product_id)

            self.queryset = ProductsTracking.objects.raw(query)
        
        return self.queryset
