from .models import Company, User, Customer, FiscalGov
from rest_framework import serializers


class CompanySerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Company
        fields = ('id', 'name', 'email', 'phoneNumber', 'rnc',
                  'address', 'creationDate', 'createdByUser')


class UserSerializer(serializers.HyperlinkedModelSerializer):
    company = CompanySerializer(many=False, read_only=True)
    company_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = User
        fields = ('id', 'company', 'company_id', 'userName', 'email',
                  'fullName', 'creationDate', 'createdByUser',
                  'userHash', 'userRole')


class CustomerSerializer(serializers.HyperlinkedModelSerializer):
    company = CompanySerializer(many=False, read_only=True)
    company_id = serializers.IntegerField(write_only=True)

    createdByUser = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Customer
        fields = ('id', 'company', 'company_id', 'firstName',
                  'lastName', 'email', 'phoneNumber', 'address',
                  'creationDate', 'createdByUser')


class FiscalGovSerializer(serializers.HyperlinkedModelSerializer):
    company = CompanySerializer(many=False, read_only=True)
    company_id = serializers.IntegerField(write_only=True)

    createdByUser = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = FiscalGov
        fields = ('id', 'company', 'company_id', 'typeDoc', 'start',
                  'end', 'current', 'dueDate', 'active',
                  'creationDate', 'createdByUser')
