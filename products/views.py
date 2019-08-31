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
    filterset_fields = ['id', 'description', 'companyId', 'model']

    def get_object(self):
        data = Product.objects.all()

        obj = get_object_or_404(
            data,
            pk=self.kwargs['pk'],
        )
        return obj


class ProductCategoryList(generics.ListCreateAPIView):
    queryset = ProductCategory.objects.all()
    serializer_class = ProductCategorySerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['id', 'description', 'companyId']

    def get_object(self):
        data = ProductCategory.objects.all()

        obj = get_object_or_404(
            data,
            pk=self.kwargs['pk'],
        )
        return obj

    def post(self, request):
        serializer = ProductCategorySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ProductsStockList(generics.ListCreateAPIView):
    queryset = ProductsStock.objects.all()
    serializer_class = ProductsStockSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['id', 'companyId', 'productId', 'modifiedByUser']

    def get_object(self):
        data = ProductsStock.objects.all()

        obj = get_object_or_404(
            data,
            pk=self.kwargs['pk'],
        )
        return obj


class ProductsTrackingList(generics.ListCreateAPIView):
    queryset = ProductsTracking.objects.all()
    serializer_class = ProductsTrackingSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['id', 'companyId',
                        'productId', 'typeTracking', 'createdByUser']

    def get_object(self):
        data = ProductsTracking.objects.all()

        obj = get_object_or_404(
            data,
            pk=self.kwargs['pk'],
        )
        return obj
