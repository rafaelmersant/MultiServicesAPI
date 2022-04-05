""" Administration views. """

# Django
from django_filters.rest_framework import DjangoFilterBackend

# Django REST framework
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

# Serializers
from . import serializers

# Others
import json

# Models
from .models import Company, User, Customer, FiscalGov, Provider

from MultiServices.paginations import StandardResultsSetPaginationAdmin


class CompanyViewSet(ModelViewSet):
    queryset = Company.objects.all()
    serializer_class = serializers.CompanySerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['id', 'name', 'rnc', 'creationDate']


class UserViewSet(ModelViewSet):
    queryset = User.objects.select_related('company').all()
    serializer_class = serializers.UserSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['id', 'email', 'name', 'userRole', 'userHash', 'creationDate']

    def get_serializer_class(self):
        if self.request.method == 'PUT':
            return serializers.UserReducedSerializer
        return serializers.UserSerializer


class UserLogin(generics.ListCreateAPIView):
    """ User Login view.

    POST call that allow to login the users.
    """
    serializer_class = serializers.UserSerializer

    def post(self, request):
        try:
            body_unicode = request.body.decode('utf-8')
            body = json.loads(body_unicode)
            email = body['email']
            password = body['password']

            user = User.objects.filter(email=email, password=password)

            if user.count() > 0:
                return Response({"id": user[0].id,
                                 "email": user[0].email,
                                 "name": user[0].name,
                                 "role": user[0].userRole,
                                 "companyId": user[0].company.id},
                                status=status.HTTP_200_OK)

            return Response("null", status=status.HTTP_404_NOT_FOUND)

        except User.DoesNotExist:
            return Response("Not Found", status=status.HTTP_404_NOT_FOUND)
        except:
            return Response("Bad Request",
                            status=status.HTTP_400_BAD_REQUEST)


class CustomerViewSet(ModelViewSet):
    queryset = Customer.objects.select_related('company').all()
    serializer_class = serializers.CustomerSerializer
    pagination_class = StandardResultsSetPaginationAdmin
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['id', 'firstName', 'lastName', 'email', 'company_id', 'phoneNumber', 'creationDate']
    search_fields = ['firstName', 'lastName', 'phoneNumber']

    def get_serializer_class(self):
        if self.request.method == 'PUT':
            return serializers.CustomerReducedSerializer
        return serializers.CustomerSerializer


class ProviderViewSet(ModelViewSet):
    queryset = Provider.objects.select_related('company').all()
    serializer_class = serializers.ProviderSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['id', 'firstName', 'lastName', 'email', 'rnc', 'company_id', 'phoneNumber', 'creationDate']
    search_fields = ['firstName', 'lastName', 'phoneNumber', 'rnc']

    def get_serializer_class(self):
        if self.request.method == 'PUT':
            return serializers.ProviderReducedSerializer
        return serializers.ProviderSerializer

    
class FiscalGovViewSet(ModelViewSet):
    queryset = FiscalGov.objects.select_related('company').all()
    serializer_class = serializers.FiscalGovSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['id', 'start', 'end', 'active', 'typeDoc', 'company_id', 'createdUser', 'creationDate']

    def get_serializer_class(self):
        if self.request.method == 'PUT':
            return serializers.FiscalGovReducedSerializer
        return serializers.FiscalGovSerializer