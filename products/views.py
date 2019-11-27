from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from .models import Product, ProductCategory, ProductsStock, \
    ProductsTracking, ProductsTrackingHeader
from .serializers import ProductSerializer, ProductCategorySerializer, \
    ProductsStockSerializer, ProductsTrackingSerializer, \
    ProductsTrackingHeaderSerializer


class ProductList(generics.ListCreateAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
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
        except:
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
    queryset = ProductsTrackingHeader.objects.all()
    serializer_class = ProductsTrackingHeaderSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['id', 'company', 'provider',
                        'ncf', 'docDate', 'createdUser']

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
    queryset = ProductsTracking.objects.all()
    serializer_class = ProductsTrackingSerializer
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
