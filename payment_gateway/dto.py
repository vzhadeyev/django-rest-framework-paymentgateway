from dataclasses import dataclass
from decimal import Decimal

from payment_gateway.models import TransactionType


@dataclass
class Transaction:
    type: TransactionType
    invoice_id: int
    money_amount: Decimal
