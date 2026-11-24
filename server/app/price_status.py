from enum import Enum


class UnavailablePrice(Enum):
    OUT_OF_STOCK = "out_of_stock"
    REGION = "unavailable_in_region"
    NOT_FOUND = "not_found"
