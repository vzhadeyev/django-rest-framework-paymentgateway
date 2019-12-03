import logging

from django.db import transaction as db_transaction
from payment_gateway.base import AbstractPaymentProvider, BasicTransactionHandler, BasicCallbackProvider, \
    BasicPaymentHandler
from payment_gateway.errors import PaymentError
from payment_gateway.models import Invoice, Transaction

from .dto import DummyTransaction

logger = logging.getLogger(__name__)


class DummyPaymentProvider(AbstractPaymentProvider):

    def try_pay(self, invoice_id: int, transaction_data: DummyTransaction) -> (Invoice, Transaction):
        transaction = self.transaction_handler.create(transaction_data)
        logger.info('Processing dummy payment.',
                    extra={'invoice_id': invoice_id, 'transaction_id': transaction.id})
        try:
            with db_transaction.atomic():
                invoice = Invoice.objects.select_for_update().get(pk=invoice_id)
                invoice = self.payment_handler.try_process_payment(invoice, transaction)
                logger.info('Successfully processed dummy payment.',
                            extra={'invoice_id': invoice_id, 'transaction_id': transaction.id})
                return invoice, transaction
        except PaymentError as e:
            self.payment_handler.handle_payment_error(e, invoice, transaction)
            logger.warning('Payment error for dummy provider.', exc_info=True, extra={'invoice_id': invoice_id,
                                                                                      'transaction_id': transaction.id})


def get_dummy_provider():
    transaction_handler = BasicTransactionHandler()
    callback_provider = BasicCallbackProvider()
    payment_handler = BasicPaymentHandler(callback_provider, transaction_handler)
    return DummyPaymentProvider(payment_handler, transaction_handler)
