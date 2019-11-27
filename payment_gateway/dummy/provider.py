from django.db import transaction as db_transaction

from payment_gateway.base import AbstractPaymentProvider, BasicTransactionHandler, BasicCallbackProvider, \
    BasicPaymentHandler
from payment_gateway.errors import PaymentError
from payment_gateway.models import Invoice, Transaction
from .dto import DummyTransaction


class DummyPaymentProvider(AbstractPaymentProvider):

    def try_pay(self, invoice_id: int, transaction_data: DummyTransaction) -> (Invoice, Transaction):
        transaction = self.transaction_handler.create(transaction_data)
        try:
            with db_transaction.atomic():
                invoice = Invoice.objects.select_for_update().get(pk=invoice_id)
                invoice = self.payment_handler.try_process_payment(invoice, transaction)
                return invoice, transaction
        except PaymentError as e:
            self.payment_handler.handle_payment_error(e, invoice, transaction)


def get_dummy_provider():
    transaction_handler = BasicTransactionHandler()
    callback_provider = BasicCallbackProvider()
    payment_handler = BasicPaymentHandler(callback_provider, transaction_handler)
    return DummyPaymentProvider(payment_handler, transaction_handler)
