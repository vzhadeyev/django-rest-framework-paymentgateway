import base64
import hashlib
import hmac
import logging
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import IntEnum

from django.db import transaction as db_transaction
from django.utils.crypto import constant_time_compare
from payment_gateway.base import AbstractPaymentProvider, BasicTransactionHandler, BasicCallbackProvider, \
    BasicPaymentHandler
from payment_gateway.dto import Transaction as TransactionDTOBase
from payment_gateway.errors import PaymentError, InvoiceExpired, InvalidMoneyAmount, InsufficientMoneyAmount, \
    InvoiceAlreadyPaid, InvoiceInvalidStatus, InvalidCurrency
from payment_gateway.models import Invoice, Transaction, CloudPaymentsTransaction, TransactionStatus, TransactionType
from payment_gateway.settings import api_settings

logger = logging.getLogger(__name__)


def get_cloudpayments_provider():
    transaction_handler = CloudPaymentsTransactionHandler()
    callback_provider = BasicCallbackProvider()
    payment_handler = CloudPaymentsPaymentHandler(callback_provider, transaction_handler)
    return CloudPaymentsPaymentProvider(payment_handler, transaction_handler)


class CloudPaymentsTransactionHandler(BasicTransactionHandler):
    @dataclass
    class TransactionDTO(TransactionDTOBase):
        type = TransactionType.CLOUDPAYMENTS

        TransactionId: int
        Amount: Decimal
        Currency: str
        DateTime: datetime
        CardFirstSix: str
        CardLastFour: str
        CardType: str
        CardExpDate: str
        TestMode: bool
        Status: str
        OperationType: str
        InvoiceId: str
        AccountId: str = None
        SubscriptionId: str = None
        TokenRecipient: str = None
        Name: str = None
        Email: str = None
        IpAddress: str = None
        IpCountry: str = None
        IpCity: str = None
        IpRegion: str = None
        IpDistrict: str = None
        Issuer: str = None
        IssuerBankCountry: str = None
        Description: str = None
        Data: dict = None

        # Pay specific fields
        GatewayName: str = None
        Token: str = None
        TotalFee: Decimal = None

    def create(self, t: TransactionDTO):
        with db_transaction.atomic():
            wt = CloudPaymentsTransaction.objects.create(
                invoice_id=t.invoice_id, money_amount=t.money_amount, type=t.type, status=TransactionStatus.PENDING,
                TransactionId=t.TransactionId, Amount=t.Amount, Currency=t.Currency, DateTime=t.DateTime,
                CardFirstSix=t.CardFirstSix, CardLastFour=t.CardLastFour, CardType=t.CardType,
                CardExpDate=t.CardExpDate, TestMode=t.TestMode, Status=t.Status, OperationType=t.OperationType,
                AccountId=t.AccountId, SubscriptionId=t.SubscriptionId, TokenRecipient=t.TokenRecipient, Name=t.Name,
                Email=t.Email, IpAddress=t.IpAddress, IpCountry=t.IpCountry, IpCity=t.IpCity, IpRegion=t.IpRegion,
                IpDistrict=t.IpDistrict, Issuer=t.Issuer, IssuerBankCountry=t.IssuerBankCountry,
                Description=t.Description, Data=t.Data
            )
        return wt


class CloudPaymentsPaymentHandler(BasicPaymentHandler):
    valid_currencies = api_settings.CLOUDPAYMENTS_VALID_CURRENCIES

    def validate_payment(self, invoice: Invoice, transaction: CloudPaymentsTransaction, raise_exc: bool = True) -> bool:
        valid = True
        valid = valid and self.validate_status_for_pay(invoice, raise_exc=raise_exc)
        valid = valid and self.validate_expiration(invoice, raise_exc=raise_exc)
        valid = valid and self.validate_money_amount(invoice, transaction.money_amount, raise_exc=raise_exc)
        valid = valid and self.validate_currency(transaction.Currency, raise_exc=raise_exc)
        return valid

    def validate_currency(self, currency: str, raise_exc: bool = True) -> bool:
        valid = currency in self.valid_currencies
        if not valid and raise_exc:
            raise InvalidCurrency()
        return valid


class CloudPaymentsResultCode(IntEnum):
    OK = 0
    INVALID_INVOICE_ID = 10
    INVALID_ACCOUNT_ID = 11
    INVALID_MONEY_AMOUNT = 12
    UNPROCESSABLE = 13
    PAYMENT_EXPIRED = 20


class CloudPaymentsPaymentProvider(AbstractPaymentProvider):

    def check(self, transaction_data: CloudPaymentsTransactionHandler.TransactionDTO) -> CloudPaymentsResultCode:
        if not Invoice.objects.filter(id=transaction_data.invoice_id).exists():
            logger.info('Invoice from Cloudpayments transaction does not exist.',
                        extra={'TransactionId': transaction_data.TransactionId,
                               'InvoiceId': transaction_data.invoice_id})
            return CloudPaymentsResultCode.INVALID_INVOICE_ID
        logger.info('Checking Cloudpayments transaction.', extra={'TransactionId': transaction_data.TransactionId,
                                                                  'invoice_id': transaction_data.invoice_id})
        transaction = self.transaction_handler.create(transaction_data)
        validation_error = None
        with db_transaction.atomic():
            invoice = Invoice.objects.select_for_update().get(pk=transaction.invoice_id)
            try:
                self.payment_handler.validate_payment(invoice, transaction, raise_exc=True)
            except PaymentError as e:
                validation_error = e
                self.payment_handler.handle_payment_error(e, invoice, transaction, raise_exc=False)
        if validation_error is not None:
            logger.info('Cloudpayments transaction validation failed.',
                        extra={'TransactionId': transaction_data.TransactionId, 'detail': validation_error.detail})
            return self.payment_error_to_code(validation_error)
        else:
            logger.info('Cloudpayments transaction validation success.',
                        extra={'TransactionId': transaction_data.TransactionId, 'invoice_id': invoice.id})
            return CloudPaymentsResultCode.OK

    def pay(self, invoice_id: int, transaction_data: CloudPaymentsTransactionHandler.TransactionDTO) -> \
            (Invoice, Transaction):
        try:
            logger.info('Paying Cloudpayments transaction.', extra={'TransactionId': transaction_data.TransactionId,
                                                                    'invoice_id': transaction_data.invoice_id})
            with db_transaction.atomic():
                transaction = CloudPaymentsTransaction.objects.get(TransactionId=transaction_data.TransactionId)
                transaction.GatewayName = transaction_data.GatewayName
                transaction.Token = transaction_data.Token
                transaction.TotalFee = transaction_data.TotalFee
                transaction.save(update_fields=['GatewayName', 'Token', 'TotalFee'])
                invoice = Invoice.objects.select_for_update().get(pk=invoice_id)
                invoice = self.payment_handler.try_process_payment(invoice, transaction)
                logger.info('Invoice paid using Cloudpayments.',
                            extra={'invoice_id': invoice_id, 'transaction_id': transaction.id})
                return invoice, transaction
        except PaymentError as e:
            self.payment_handler.handle_payment_error(e, invoice, transaction, raise_exc=False)
            logger.warning('Payment error for Cloudpayments provider.',
                           exc_info=True, extra={'invoice_id': invoice_id, 'transaction_id': transaction.id})
            raise e

    def payment_error_to_code(self, error: PaymentError):
        if isinstance(error, (InvalidMoneyAmount, InsufficientMoneyAmount)):
            return CloudPaymentsResultCode.INVALID_MONEY_AMOUNT
        elif isinstance(error, InvoiceExpired):
            return CloudPaymentsResultCode.PAYMENT_EXPIRED
        elif isinstance(error, InvoiceAlreadyPaid):
            return CloudPaymentsResultCode.UNPROCESSABLE
        elif isinstance(error, InvoiceInvalidStatus):
            return CloudPaymentsResultCode.UNPROCESSABLE
        else:
            return CloudPaymentsResultCode.UNPROCESSABLE


class NotificationValidator(object):
    api_secret = bytes(api_settings.CLOUDPAYMENTS_API_SECRET, 'utf-8')

    def calculate_hmac(self, message: bytes):
        return base64.b64encode(hmac.new(self.api_secret, message, digestmod=hashlib.sha256).digest())

    def validate(self, value, expected_value):
        calculated_value = self.calculate_hmac(value)
        return constant_time_compare(calculated_value, expected_value)
