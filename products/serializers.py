from .models import Product, ProductCategory, ProductsStock, ProductsTracking
from administration.models import Company
from administration.serializers import CompanySerializer
from rest_framework import serializers


class ProductCategorySerializer(serializers.HyperlinkedModelSerializer):
    # companyId = serializers.StringRelatedField(read_only=True)
    company_Id = serializers.PrimaryKeyRelatedField(read_only=True)
    # company = CompanySerializer(read_only=True)

    def create(self, validated_data):
        return ProductCategory.objects.create(**validated_data)

    class Meta:
        model = ProductCategory
        fields = ('id', 'description', 'company_Id')


class ProductSerializer(serializers.HyperlinkedModelSerializer):
    companyId = serializers.StringRelatedField(read_only=True)
    categoryId = serializers.StringRelatedField(read_only=True)
    createdByUser = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Product
        fields = ('id', 'companyId', 'description', 'descriptionLong',
                  'price', 'cost', 'itbis', 'categoryId', 'measure', 'model',
                  'creationDate', 'createdByUser')


class ProductsStockSerializer(serializers.HyperlinkedModelSerializer):
    companyId = serializers.StringRelatedField(read_only=True)
    productId = serializers.StringRelatedField(read_only=True)
    modifiedByUser = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = ProductsStock
        fields = ('id', 'companyId', 'productId', 'quantityAvailable',
                  'quantityHold', 'lastUpdated', 'modifiedByUser')


class ProductsTrackingSerializer(serializers.HyperlinkedModelSerializer):
    companyId = serializers.StringRelatedField(read_only=True)
    productId = serializers.StringRelatedField(read_only=True)
    createdByUser = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = ProductsTracking
        fields = ('id', 'companyId', 'productId', 'typeTracking',
                  'quantity', 'creationDate', 'createdByUser')
