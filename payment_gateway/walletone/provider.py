import hashlib
import logging
from base64 import b64encode
from collections import defaultdict
from datetime import datetime

from django.db import transaction as db_transaction, IntegrityError
from django.utils.translation import ugettext_lazy as _
from payment_gateway.base import AbstractPaymentProvider, BasicTransactionHandler, BasicCallbackProvider, \
    BasicPaymentHandler
from payment_gateway.errors import InvalidMoneyAmount, InvoiceExpired, PaymentError
from payment_gateway.models import WalletOneTransaction, Invoice, Transaction, InvoiceStatus, TransactionStatus
from payment_gateway.settings import api_settings

from .dto import WalletOneTransaction as WalletOneTransactionDTO

logger = logging.getLogger(__name__)


def get_walletone_provider():
    transaction_handler = WalletOneTransactionHandler()
    callback_provider = BasicCallbackProvider()
    payment_handler = BasicPaymentHandler(callback_provider, transaction_handler)
    return WalletOnePaymentProvider(payment_handler, transaction_handler)


class WalletOneSignEncoder(object):
    SECRET_KEY = api_settings.WALLETONE_SECRET_KEY

    def _get_signature_string(self, params):
        icase_key = lambda s: str(s).lower()

        lists_by_keys = defaultdict(list)
        if isinstance(params, dict):
            params = params.items()
        for key, value in params:
            lists_by_keys[key].append(value)

        s = sorted(lists_by_keys, key=icase_key)
        str_buff = ''
        for key in sorted(lists_by_keys, key=icase_key):
            if key == 'WMI_SIGNATURE':
                continue
            for value in sorted(lists_by_keys[key], key=icase_key):
                if isinstance(value, datetime):
                    str_buff += str(value.replace(tzinfo=None))
                else:
                    str_buff += str(value)
        str_buff += self.SECRET_KEY
        return str_buff

    def _get_signature(self, fields):
        hash_string = hashlib.md5(self._get_signature_string(fields).encode('1251')).digest()
        signature = b64encode(hash_string)
        return signature


class WalletOneException(Exception):
    def __init__(self, error_msg):
        self.error_msg = error_msg


class WalletOnePaymentProvider(WalletOneSignEncoder, AbstractPaymentProvider):

    def validate_signature(self, attrs):
        signature = attrs.get('WMI_SIGNATURE', '')
        value = self._get_signature(attrs).decode()
        if signature != value:
            raise WalletOneException('WMI_RESULT=RETRY&WMI_DESCRIPTION=WMI_SIGNATURE error')
        return attrs

    def get_encoded_description(self, invoice: Invoice) -> str:
        desc = invoice.details.get(api_settings.WALLETONE_DETAIL_FIELD, _('Purchase payment'))
        if len(desc) > 255:
            desc = "%s..." % desc[:252]
        return 'BASE64:%s' % b64encode(desc.encode('utf-8')).decode()

    def make_signed_invoice(self, invoice: Invoice) -> list:
        overridden_data = invoice.details.get('WALLET_ONE_OVERRIDE', {})
        data = [('WMI_MERCHANT_ID', api_settings.WALLETONE_MERCHANT_ID),
                ('WMI_CURRENCY_ID', api_settings.WALLETONE_CURRENCY_ID),
                ('WMI_DESCRIPTION', self.get_encoded_description(invoice)),
                ('WMI_SUCCESS_URL', overridden_data.get('WMI_SUCCESS_URL', api_settings.WALLETONE_SUCCESS_URL)),
                ('WMI_FAIL_URL', overridden_data.get('WMI_FAIL_URL', api_settings.WALLETONE_FAIL_URL)),
                ('WMI_PAYMENT_AMOUNT', str(invoice.total)),
                ('WMI_PAYMENT_NO', str(invoice.id)),
                ('WMI_EXPIRED_DATE', invoice.expires_at.replace(microsecond=0).replace(tzinfo=None).isoformat())]
        data.append(('WMI_SIGNATURE', self._get_signature(data).decode()))
        return data

    def try_pay(self, invoice_id: int, transaction_data: WalletOneTransactionDTO) -> (Invoice, Transaction):
        invoice_id = transaction_data.WMI_PAYMENT_NO
        logger.info('Processing WalletOne payment.',
                    extra={'invoice_id': invoice_id, 'WMI_ORDER_ID': transaction_data.WMI_ORDER_ID})
        transaction_data.money_amount = transaction_data.WMI_PAYMENT_AMOUNT
        if WalletOneTransaction.objects.filter(WMI_ORDER_ID=transaction_data.WMI_ORDER_ID).exists():
            wt = WalletOneTransaction.objects.select_related('transaction').get(
                WMI_ORDER_ID=transaction_data.WMI_ORDER_ID)
            wt.WMI_NOTIFY_COUNT = transaction_data.WMI_NOTIFY_COUNT
            wt.WMI_LAST_NOTIFY_DATE = transaction_data.WMI_LAST_NOTIFY_DATE
            wt.WMI_INVOICE_OPERATIONS = transaction_data.WMI_INVOICE_OPERATIONS
            wt.money_amount = transaction_data.money_amount
            wt.save(
                update_fields=['WMI_NOTIFY_COUNT', 'WMI_LAST_NOTIFY_DATE', 'WMI_INVOICE_OPERATIONS', 'money_amount'])
            transaction = wt.transaction
        else:
            transaction = self.transaction_handler.create(transaction_data)
        error_message = 'WMI_RESULT=RETRY&WMI_DESCRIPTION=WMI_PAYMENT_NO error'
        try:
            try:
                with db_transaction.atomic():
                    invoice = Invoice.objects.select_for_update().get(id=invoice_id)
                    if invoice.status == InvoiceStatus.PAID and transaction.id == invoice.success_transaction_id:
                        logger.info('WalletOne payment was already made returning old result.',
                                    extra={'invoice_id': invoice_id, 'WMI_ORDER_ID': transaction_data.WMI_ORDER_ID})
                        return invoice, transaction
                    invoice = self.payment_handler.try_process_payment(invoice, transaction)
                    logger.info('WalletOne payment success.',
                                extra={'invoice_id': invoice_id, 'transaction_id': transaction.id,
                                       'WMI_ORDER_ID': transaction_data.WMI_ORDER_ID})
                    return invoice, transaction
            except PaymentError as e:
                self.payment_handler.handle_payment_error(e, invoice, transaction)
        except (Invoice.DoesNotExist, IntegrityError):
            error_message = 'WMI_RESULT=RETRY&WMI_DESCRIPTION=WMI_PAYMENT_NO error'
        except InvalidMoneyAmount:
            error_message = 'WMI_RESULT=RETRY&WMI_DESCRIPTION=WMI_PAYMENT_AMOUNT not enough'
        except InvoiceExpired:
            error_message = 'WMI_RESULT=RETRY&WMI_DESCRIPTION=WMI_PAYMENT_NO Payment timeout'
        raise WalletOneException(error_message)


class WalletOneTransactionHandler(BasicTransactionHandler):
    def create(self, transaction: WalletOneTransactionDTO):
        with db_transaction.atomic():
            # t = super().create(transaction)
            wt = WalletOneTransaction.objects.create(
                invoice_id=transaction.invoice_id,
                money_amount=transaction.money_amount,
                type=transaction.type,
                status=TransactionStatus.PENDING,
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
                WMI_NOTIFY_COUNT=transaction.WMI_NOTIFY_COUNT,
                WMI_EXTERNAL_ACCOUNT_ID=transaction.WMI_EXTERNAL_ACCOUNT_ID,
                WMI_AUTO_ACCEPT=transaction.WMI_AUTO_ACCEPT,
                WMI_LAST_NOTIFY_DATE=transaction.WMI_LAST_NOTIFY_DATE,
                WMI_INVOICE_OPERATIONS=transaction.WMI_INVOICE_OPERATIONS,
                WMI_PAYMENT_TYPE=transaction.WMI_PAYMENT_TYPE
            )
        return wt
