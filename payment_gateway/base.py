import importlib
import logging
from decimal import Decimal

from django.db import transaction as db_transaction
from django.utils import timezone

from payment_gateway.dto import Transaction as TransactionDTO
from payment_gateway.errors import InvalidMoneyAmount, InvoiceExpired, InvoiceAlreadyPaid, InvoiceInvalidStatus, \
    InsufficientMoneyAmount, PaymentError
from payment_gateway.models import Transaction, InvoiceStatus, TransactionStatus, TransactionStatusChange, \
    InvoiceStatusChange, Invoice

logger = logging.getLogger(__name__)


class AbstractPaymentHandler(object):

    def try_process_payment(self, invoice: Invoice, transaction: Transaction) -> Invoice:
        raise NotImplementedError

    def handle_payment_error(self, error: PaymentError, invoice: Invoice, transaction: Transaction):
        raise NotImplementedError

    def validate_payment(self, invoice: Invoice, transaction: Transaction, raise_exc: bool) -> bool:
        raise NotImplementedError

    def validate_expiration(self, invoice: Invoice, raise_exc: bool = True) -> bool:
        raise NotImplementedError

    def validate_status_for_pay(self, invoice: Invoice, raise_exc: bool = True) -> bool:
        raise NotImplementedError

    def on_success(self, invoice: Invoice, *args, **kwargs) -> Invoice:
        raise NotImplementedError

    def on_fail(self, invoice: Invoice, *args, **kwargs) -> Invoice:
        raise NotImplementedError


class AbstractTransactionHandler(object):
    def create(self, transaction: TransactionDTO):
        raise NotImplementedError

    def set_expired(self, transaction: Transaction):
        raise NotImplementedError

    def set_invalid_money_amount(self, transaction: Transaction):
        raise NotImplementedError

    def set_success(self, transaction: Transaction):
        raise NotImplementedError

    def set_error(self, transaction: Transaction):
        raise NotImplementedError

    def update_transaction_status(self, transaction: Transaction, status: TransactionStatus):
        raise NotImplementedError


class AbstractCallbackProvider(object):

    def success(self, *args, **kwargs) -> Invoice:
        raise NotImplementedError

    def fail(self, *args, **kwargs) -> Invoice:
        raise NotImplementedError


class AbstractPaymentProvider(object):
    def __init__(self, payment_handler: AbstractPaymentHandler, transaction_handler: AbstractTransactionHandler):
        self.payment_handler = payment_handler
        self.transaction_handler = transaction_handler

    def try_pay(self, invoice_id: int, transaction_data: object) -> (Invoice, Transaction):
        raise NotImplementedError


class BasicCallbackProvider(AbstractCallbackProvider):

    def success(self, invoice, *args, **kwargs):
        logger.info('Calling success callback for invoice.', extra={'invoice_id': invoice.pk,
                                                                    'callback': invoice.success_callback})
        mod_name, func_name = invoice.success_callback.rsplit('.', 1)
        mod = importlib.import_module(mod_name)
        func = getattr(mod, func_name)
        func(invoice.id)
        logger.info('Executed success callback for invoice', extra={'invoice_id': invoice.pk,
                                                                    'callback': invoice.success_callback})
        return invoice

    def fail(self, invoice, *args, **kwargs):
        logger.info('Calling fail callback for invoice.', extra={'invoice_id': invoice.pk,
                                                                 'callback': invoice.fail_callback})
        if invoice.fail_callback is not None:
            mod_name, func_name = invoice.fail_callback.rsplit('.', 1)
            mod = importlib.import_module(mod_name)
            func = getattr(mod, func_name)
            func(invoice.id)
            logger.info('Executed fail callback for invoice.', extra={'invoice_id': invoice.pk,
                                                                      'callback': invoice.fail_callback})
        return invoice


class BasicTransactionHandler(AbstractTransactionHandler):
    def create(self, transaction: TransactionDTO):
        return Transaction.objects.create(
            invoice_id=transaction.invoice_id,
            money_amount=transaction.money_amount,
            type=transaction.type,
            status=TransactionStatus.PENDING
        )

    def set_expired(self, transaction: Transaction):
        return self.update_transaction_status(transaction, TransactionStatus.INVOICE_EXPIRED)

    def set_invalid_money_amount(self, transaction: Transaction):
        return self.update_transaction_status(transaction, TransactionStatus.INVALID_MONEY_AMOUNT)

    def set_success(self, transaction: Transaction):
        return self.update_transaction_status(transaction, TransactionStatus.SUCCESS)

    def set_error(self, transaction: Transaction):
        return self.update_transaction_status(transaction, TransactionStatus.ERROR)

    @db_transaction.atomic()
    def update_transaction_status(self, transaction: Transaction, status: TransactionStatus) -> Transaction:
        prev_status = transaction.status
        transaction.status = status
        transaction.save(update_fields=['status', 'modified_at'])
        TransactionStatusChange.objects.create(
            transaction=transaction,
            from_status=prev_status,
            to_status=transaction.status
        )
        return transaction


class BasicPaymentHandler(AbstractPaymentHandler):

    def __init__(self, callback_provider: AbstractCallbackProvider, transaction_handler: AbstractTransactionHandler):
        self.callback_provider = callback_provider
        self.transaction_handler = transaction_handler

    def try_process_payment(self, invoice: Invoice, transaction: Transaction) -> Invoice:
        assert db_transaction.get_connection().in_atomic_block

        self.validate_payment(invoice, transaction, raise_exc=True)
        invoice = self.make_invoice_success(invoice, transaction)
        return self.on_success(invoice)

    def handle_payment_error(self, error: PaymentError, invoice: Invoice, transaction: Transaction):
        if isinstance(error, (InvalidMoneyAmount, InsufficientMoneyAmount)):
            self.transaction_handler.set_invalid_money_amount(transaction)
        elif isinstance(error, InvoiceExpired):
            self.make_invoice_expired(invoice, transaction)
        else:
            self.transaction_handler.set_error(transaction)
        raise error

    def set_invoice_status(self, invoice: Invoice, status: InvoiceStatus) -> (Invoice, InvoiceStatus):
        old_status = invoice.status
        invoice.status = status
        return invoice, old_status

    @db_transaction.atomic()
    def make_invoice_success(self, invoice: Invoice, transaction: Transaction) -> Invoice:
        transaction = self.transaction_handler.set_success(transaction)
        invoice.success_transaction = transaction
        invoice.captured_total = transaction.money_amount
        invoice, old_status = self.set_invoice_status(invoice, InvoiceStatus.PAID)
        invoice.save(update_fields=['status', 'success_transaction', 'modified_at', 'captured_total'])
        self.write_invoice_history(invoice, new_status=invoice.status, old_status=old_status)
        return invoice

    @db_transaction.atomic()
    def make_invoice_expired(self, invoice: Invoice, transaction: Transaction) -> Invoice:
        self.transaction_handler.set_expired(transaction)
        if invoice.status != InvoiceStatus.EXPIRED:
            invoice, old_status = self.set_invoice_status(invoice, InvoiceStatus.EXPIRED)
            invoice.save(update_fields=['status', 'modified_at'])
            self.write_invoice_history(invoice, invoice.status, old_status)
        return invoice

    def write_invoice_history(self, invoice: Invoice, new_status: int, old_status: int) -> InvoiceStatusChange:
        return InvoiceStatusChange.objects.create(
            invoice=invoice,
            from_status=old_status,
            to_status=new_status
        )

    def validate_payment(self, invoice: Invoice, transaction: Transaction, raise_exc: bool = True) -> bool:
        valid = True
        valid = valid and self.validate_status_for_pay(invoice, raise_exc=raise_exc)
        valid = valid and self.validate_expiration(invoice, raise_exc=raise_exc)
        valid = valid and self.validate_money_amount(invoice, transaction.money_amount, raise_exc=raise_exc)
        return valid

    def validate_money_amount(self, invoice: Invoice, money_amount: Decimal, raise_exc: bool = True) -> bool:
        valid = invoice.total <= money_amount
        if not valid and raise_exc:
            if invoice.total > money_amount:
                raise InsufficientMoneyAmount()
            raise InvalidMoneyAmount()
        return valid

    def validate_expiration(self, invoice: Invoice, raise_exc: bool = True) -> bool:
        if invoice.expires_at is None:
            return True
        valid = invoice.expires_at > timezone.now()
        if not valid and raise_exc:
            raise InvoiceExpired()
        return valid

    def validate_status_for_pay(self, invoice: Invoice, raise_exc: bool = True) -> bool:
        valid = invoice.status == InvoiceStatus.PENDING
        if not valid and raise_exc:
            if invoice.status == InvoiceStatus.EXPIRED:
                raise InvoiceExpired()
            elif invoice.status == InvoiceStatus.PAID:
                raise InvoiceAlreadyPaid()
            else:
                raise InvoiceInvalidStatus()
        return valid

    def on_success(self, invoice: Invoice, *args, **kwargs) -> Invoice:
        return self.callback_provider.success(invoice, *args, **kwargs)

    def on_fail(self, invoice: Invoice, *args, **kwargs) -> Invoice:
        return self.callback_provider.fail(invoice, *args, **kwargs)
