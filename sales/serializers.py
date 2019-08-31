from .models import InvoicesHeader, InvoicesDetail
from rest_framework import serializers


class InvoicesHeaderSerializer(serializers.HyperlinkedModelSerializer):
    companyId = serializers.StringRelatedField(read_only=True)
    customerId = serializers.StringRelatedField(read_only=True)
    createdByUser = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = InvoicesHeader
        fields = ('id', 'companyId', 'customerId', 'paymentMethod',
                  'ncf', 'creationDate', 'createdByUser')


class InvoicesDetailSerializer(serializers.HyperlinkedModelSerializer):
    invoiceId = serializers.StringRelatedField(read_only=True)
    productId = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = InvoicesDetail
        fields = ('id', 'invoiceId', 'productId', 'price',
                  'cost', 'discount', 'creationDate')
