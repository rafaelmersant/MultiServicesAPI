""" Administration views. """

# Django
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404

# Django REST framework
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.viewsets import ModelViewSet

# Models
from .models import Company, User, Customer, FiscalGov, Provider

# Serializers
from .serializers import CompanySerializer, UserSerializer, \
    CustomerSerializer, FiscalGovSerializer, ProviderSerializer

# Others
import json


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 15
    page_size_query_param = 'page_size'
    max_page_size = 15


class CompanyViewSet(ModelViewSet):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['id', 'name', 'rnc', 'creationDate']


class UserViewSet(ModelViewSet):
    queryset = User.objects.select_related('company').all()
    serializer_class = UserSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['id', 'email', 'name', 'userRole', 'userHash', 'creationDate']


class UserLogin(generics.ListCreateAPIView):
    """ User Login view.

    POST call that allow to login the users.
    """

    serializer_class = UserSerializer

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
    serializer_class = CustomerSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['id', 'firstName', 'lastName', 'email', 'company_id', 'phoneNumber', 'creationDate']
    search_fields = ['firstName', 'lastName', 'phoneNumber']


class ProviderViewSet(ModelViewSet):
    queryset = Provider.objects.select_related('company').all()
    serializer_class = ProviderSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['id', 'firstName', 'lastName', 'email', 'rnc', 'company_id', 'phoneNumber', 'creationDate']
    search_fields = ['firstName', 'lastName', 'phoneNumber', 'rnc']

    
class FiscalGovViewSet(ModelViewSet):
    queryset = FiscalGov.objects.select_related('company').all()
    serializer_class = FiscalGovSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['id', 'start', 'end', 'active', 'typeDoc', 'company_id', 'createdUser', 'creationDate']