from datetime import datetime
from decimal import Decimal

from payment_gateway.dto import Transaction
from payment_gateway.models import TransactionType


class WalletOneTransaction(Transaction):
    type = TransactionType.WALLETONE
    WMI_ORDER_ID: str
    WMI_MERCHANT_ID: str
    WMI_PAYMENT_AMOUNT: Decimal
    WMI_COMMISSION_AMOUNT: Decimal
    WMI_CURRENCY_ID: int
    WMI_TO_USER_ID: str
    WMI_PAYMENT_NO: str
    WMI_DESCRIPTION: str
    WMI_SUCCESS_URL: str
    WMI_FAIL_URL: str
    WMI_EXPIRED_DATE: datetime
    WMI_CREATE_DATE: datetime
    WMI_UPDATE_DATE: datetime
    WMI_ORDER_STATE: str
    WMI_NOTIFY_COUNT: int
    WMI_EXTERNAL_ACCOUNT_ID: str
    WMI_AUTO_ACCEPT: str
    WMI_LAST_NOTIFY_DATE: datetime
    WMI_INVOICE_OPERATIONS: str
    WMI_PAYMENT_TYPE: str
