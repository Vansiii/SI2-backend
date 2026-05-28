"""
Core pagination classes for consistent API responses.
"""

from rest_framework.pagination import PageNumberPagination


class StandardResultsSetPagination(PageNumberPagination):
    """Default pagination: 20 items per page, configurable via query param."""

    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100
