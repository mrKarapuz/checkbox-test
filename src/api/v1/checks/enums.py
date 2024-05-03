from enum import Enum


class PaymentType(str, Enum):
    CASH = 'CASH'
    CASHLESS = 'CASHLESS'
