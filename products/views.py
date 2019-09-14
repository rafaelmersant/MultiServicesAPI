from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from rest_framework import generics
from .models import Product, ProductCategory, ProductsStock, ProductsTracking
from .serializers import ProductSerializer, ProductCategorySerializer, \
    ProductsStockSerializer, ProductsTrackingSerializer


class ProductList(generics.ListCreateAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['id', 'description', 'company', 'model']

    def delete(self, request, pk=None):
        product = Product.objects.get(pk=pk)
        product.delete()
        return Response("deleted")

    def put(self, request, pk, format=None):
        product = Product.objects.get(pk=pk)
        serializer = ProductSerializer(product, data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProductCategoryList(generics.ListCreateAPIView):
    queryset = ProductCategory.objects.all()
    serializer_class = ProductCategorySerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['id', 'description', 'company']

    def delete(self, request, pk=None):
        productCategory = ProductCategory.objects.get(pk=pk)
        productCategory.delete()
        return Response("deleted")

    def put(self, request, pk, format=None):
        productCategory = ProductCategory.objects.get(pk=pk)
        serializer = ProductCategorySerializer(
            productCategory, data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProductsStockList(generics.ListCreateAPIView):
    queryset = ProductsStock.objects.all()
    serializer_class = ProductsStockSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['id', 'company', 'product', 'modifiedByUser']

    def delete(self, request, pk=None):
        productsStock = ProductsStock.objects.get(pk=pk)
        productsStock.delete()
        return Response("deleted")

    def put(self, request, pk, format=None):
        productsStock = ProductsStock.objects.get(pk=pk)
        serializer = ProductsCategorySerializer(
            productsStock, data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProductsTrackingList(generics.ListCreateAPIView):
    queryset = ProductsTracking.objects.all()
    serializer_class = ProductsTrackingSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['id', 'company',
                        'product', 'typeTracking', 'createdByUser']

    def delete(self, request, pk=None):
        productsTracking = ProductsTracking.objects.get(pk=pk)
        productsTracking.delete()
        return Response("deleted")

    def put(self, request, pk, format=None):
        productsTracking = ProductsTracking.objects.get(pk=pk)
        serializer = ProductsTrackingSerializer(
            productsTracking, data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
