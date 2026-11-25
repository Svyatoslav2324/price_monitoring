from contextlib import contextmanager

from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError

from .base import MarketplaceError, ProductNotFound, UnsupportedURL


class MarketplaceUnavailable(APIException):
    status_code = status.HTTP_502_BAD_GATEWAY
    default_code = "marketplace_unavailable"


class MarketplaceProductNotFound(APIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_code = "product_not_found"


@contextmanager
def as_api_error(field: str = "url"):
    """Переводит ошибки клиентов маркетплейсов в HTTP-ответы DRF."""
    try:
        yield
    except UnsupportedURL as e:
        raise ValidationError({field: [str(e)]}) from e
    except ProductNotFound as e:
        raise MarketplaceProductNotFound(str(e)) from e
    except MarketplaceError as e:
        raise MarketplaceUnavailable(str(e)) from e
