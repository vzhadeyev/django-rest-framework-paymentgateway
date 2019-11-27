from payment_gateway.dto import Transaction
from payment_gateway.models import TransactionType


class DummyTransaction(Transaction):
    type = TransactionType.DUMMY
