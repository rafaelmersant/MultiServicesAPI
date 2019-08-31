from .models import Company, User, Customer, FiscalGov
from rest_framework import serializers


class CompanySerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Company
        fields = ('id', 'name', 'email', 'phoneNumber', 'rnc',
                  'address', 'creationDate', 'createdByUser')


class UserSerializer(serializers.HyperlinkedModelSerializer):
    companyId = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = User
        fields = ('id', 'companyId', 'userName', 'email',
                  'fullName', 'creationDate', 'createdByUser')


class CustomerSerializer(serializers.HyperlinkedModelSerializer):
    companyId = serializers.StringRelatedField(read_only=True)
    createdByUser = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Customer
        fields = ('id', 'companyId', 'firstName', 'lastName', 'email',
                  'phoneNumber', 'address', 'creationDate', 'createdByUser')


class FiscalGovSerializer(serializers.HyperlinkedModelSerializer):
    companyId = serializers.StringRelatedField(read_only=True)
    createdByUser = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = FiscalGov
        fields = ('id', 'companyId', 'typeDoc', 'start', 'end', 'current',
                  'dueDate', 'active', 'creationDate', 'createdByUser')
