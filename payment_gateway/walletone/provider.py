import hashlib
from base64 import b64encode
from datetime import datetime

from django.db import transaction as db_transaction, IntegrityError
from django.utils.translation import ugettext_lazy as _

from payment_gateway.base import AbstractPaymentProvider, BasicTransactionHandler, BasicCallbackProvider, \
    BasicPaymentHandler
from payment_gateway.errors import InvalidMoneyAmount, InvoiceExpired, PaymentError
from payment_gateway.models import WalletOneTransaction, Invoice, Transaction
from payment_gateway.settings import api_settings
from .dto import WalletOneTransaction as WalletOneTransactionDTO


def get_walletone_provider():
    transaction_handler = WalletOneTransactionHandler()
    callback_provider = BasicCallbackProvider()
    payment_handler = BasicPaymentHandler(callback_provider, transaction_handler)
    return WalletOnePaymentProvider(payment_handler, transaction_handler)


class WalletOneSignEncoder(object):
    SECRET_KEY = api_settings.WALLETONE_SECRET_KEY

    def _get_signature_string(self, fields):
        signature_string = ''
        for name in sorted(fields.keys(), key=lambda s: s.lower()):
            if name == 'WMI_SIGNATURE':
                continue
            if isinstance(fields[name], datetime):
                signature_string += str(fields[name].replace(tzinfo=None))
            else:
                signature_string += str(fields[name])
        signature_string += self.SECRET_KEY
        return signature_string

    def _get_signature(self, fields):
        hash_string = hashlib.sha1(self._get_signature_string(fields).encode('1251')).digest()
        return b64encode(hash_string)


class WalletOneException(Exception):
    def __init__(self, error_msg):
        self.error_msg = error_msg


class WalletOnePaymentProvider(WalletOneSignEncoder, AbstractPaymentProvider):

    def validate_signature(self, attrs):
        signature = attrs.get('WMI_SIGNATURE', '')
        if signature != self._get_signature(attrs).decode():
            raise PaymentError('WMI_SIGNATURE error')
        return attrs

    def get_encoded_description(self, invoice: Invoice) -> str:
        desc = invoice.details.get(api_settings.WALLETONE_DETAIL_FIELD, _('Purchase payment'))
        if len(desc) > 255:
            desc = "%s..." % desc[:252]
        return 'BASE64:%s' % b64encode(desc.encode('utf-8')).decode()

    def make_signed_invoice(self, invoice: Invoice) -> dict:
        data = {
            'WMI_MERCHANT_ID': api_settings.WALLETONE_MERCHANT_ID,
            'WMI_CURRENCY_ID': api_settings.WALLETONE_CURRENCY_ID,
            'WMI_DESCRIPTION': self.get_encoded_description(invoice),
            'WMI_SUCCESS_URL': api_settings.WALLETONE_SUCCESS_URL,
            'WMI_FAIL_URL': api_settings.WALLETONE_FAIL_URL,
            'WMI_PAYMENT_AMOUNT': invoice.total,
            'WMI_PAYMENT_NO': invoice.id,
            'WMI_EXPIRED_DATE': invoice.expires_at.replace(microsecond=0).replace(tzinfo=None).isoformat()
        }
        data['WMI_SIGNATURE'] = self._get_signature(data).decode()
        return data

    def try_pay(self, invoice_id: int, transaction_data: WalletOneTransactionDTO) -> (Invoice, Transaction):
        invoice_id = transaction_data.WMI_PAYMENT_NO

        transaction_data.money_amount = transaction_data.WMI_PAYMENT_AMOUNT
        transaction = self.transaction_handler.create(transaction_data)
        error_message = 'WMI_RESULT=RETRY&WMI_DESCRIPTION=WMI_PAYMENT_NO error'
        try:
            try:
                with db_transaction.atomic():
                    invoice = Invoice.objects.select_for_update().get(id=invoice_id)
                    if WalletOneTransaction.objects.filter(WMI_ORDER_ID=transaction_data.WMI_ORDER_ID).exists():
                        wt = WalletOneTransaction.objects.select_related('transaction').get(
                            WMI_ORDER_ID=transaction_data.WMI_ORDER_ID)
                        return invoice, wt
                    invoice = self.payment_handler.try_process_payment(invoice, transaction)
                    return invoice, transaction
            except PaymentError as e:
                self.payment_handler.handle_payment_error(e, invoice, transaction)
        except (Invoice.DoesNotExist, IntegrityError):
            error_message = 'WMI_RESULT=RETRY&WMI_DESCRIPTION=WMI_PAYMENT_NO error'
        except InvalidMoneyAmount:
            error_message = 'WMI_RESULT=RETRY&WMI_DESCRIPTION=WMI_PAYMENT_AMOUNT not enough'
        except InvoiceExpired:
            error_message = 'WMI_RESULT=RETRY&WMI_DESCRIPTION=WMI_PAYMENT_NO Payment timeout'
        # TODO check WalletOne docs for proper message
        raise WalletOneException(error_message)


class WalletOneTransactionHandler(BasicTransactionHandler):
    def create(self, transaction: WalletOneTransactionDTO):
        assert db_transaction.get_connection().in_atomic_block
        t = super().create(transaction)
        wt = WalletOneTransaction.objects.create(
            transaction=t,
            WMI_ORDER_ID=transaction.WMI_ORDER_ID,
            WMI_MERCHANT_ID=transaction.WMI_MERCHANT_ID,
            WMI_PAYMENT_AMOUNT=transaction.WMI_PAYMENT_AMOUNT,
            WMI_COMMISSION_AMOUNT=transaction.WMI_COMMISSION_AMOUNT,
            WMI_CURRENCY_ID=transaction.WMI_CURRENCY_ID,
            WMI_TO_USER_ID=transaction.WMI_TO_USER_ID,
            WMI_PAYMENT_NO=transaction.WMI_PAYMENT_NO,
            WMI_DESCRIPTION=transaction.WMI_DESCRIPTION,
            WMI_SUCCESS_URL=transaction.WMI_SUCCESS_URL,
            WMI_FAIL_URL=transaction.WMI_FAIL_URL,
            WMI_EXPIRED_DATE=transaction.WMI_EXPIRED_DATE,
            WMI_CREATE_DATE=transaction.WMI_CREATE_DATE,
            WMI_UPDATE_DATE=transaction.WMI_UPDATE_DATE,
            WMI_ORDER_STATE=transaction.WMI_ORDER_STATE,
            WMI_NOTIFY_COUNT=transaction.WMI_CREATE_DATE,
            WMI_EXTERNAL_ACCOUNT_ID=transaction.WMI_EXTERNAL_ACCOUNT_ID,
            WMI_AUTO_ACCEPT=transaction.WMI_AUTO_ACCEPT,
            WMI_LAST_NOTIFY_DATE=transaction.WMI_LAST_NOTIFY_DATE,
            WMI_INVOICE_OPERATIONS=transaction.WMI_INVOICE_OPERATIONS,
            WMI_PAYMENT_TYPE=transaction.WMI_PAYMENT_TYPE
        )
        return wt
