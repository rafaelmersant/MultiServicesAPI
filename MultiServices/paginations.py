from rest_framework.pagination import PageNumberPagination


class InvoiceListPagination(PageNumberPagination):
    def get_page_size(self, request):
        customer = request.query_params.get('customer', None)
        start_date = request.query_params.get('start_date', None)
        end_date = request.query_params.get('end_date', None)

        if customer is not None or \
            start_date is not None or \
            end_date is not None:
            return 9999999
        else:
            return 10


class ProviderInventoryListPagination(PageNumberPagination):
    def get_page_size(self, request):
        provider_name = request.query_params.get('provider_name', None)
        year = request.query_params.get('year', None)
        all = request.query_params.get('all', None)

        if (provider_name is not None and len(provider_name) > 0) \
             or year is not None or all is not None:
            return 9999999
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



