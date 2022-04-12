from rest_framework.pagination import PageNumberPagination


class InvoiceListPagination(PageNumberPagination):
    def get_page_size(self, request):
        customer = request.query_params.get('customer', None)
        if customer is not None:
            return 9000
        else:
            return 10


class ProviderInventoryListPagination(PageNumberPagination):
    def get_page_size(self, request):
        provider_name = request.query_params.get('provider_name', None)
        if provider_name is not None and len(provider_name) > 0:
            return 999999
        else:
            return 10


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 10


class StandardResultsSetPaginationAdmin(PageNumberPagination):
    page_size = 15
    page_size_query_param = 'page_size'
    max_page_size = 15


class StandardResultsSetPaginationMedium(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 20


class StandardResultsSetPaginationHigh(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 50


class StandardResultsSetPaginationLevelHighest(PageNumberPagination):
    page_size = 200
    page_size_query_param = 'page_size'
    max_page_size = 200



