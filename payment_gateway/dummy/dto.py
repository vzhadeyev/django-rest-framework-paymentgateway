from dataclasses import dataclass

from payment_gateway.dto import Transaction
from payment_gateway.models import TransactionType


@dataclass
class DummyTransaction(Transaction):
    type = TransactionType.DUMMY
