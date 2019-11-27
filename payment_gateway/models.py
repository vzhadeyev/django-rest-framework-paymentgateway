from enum import Enum

from django.contrib.postgres.fields import JSONField
from django.db import models
from django.utils.translation import ugettext_lazy as _


class ModelChoice(Enum):
    @classmethod
    def choices(cls):
        return [(c.value, _(c.name)) for c in cls]


class InvoiceStatus(int, ModelChoice):
    PENDING = 0
    PAID = 1
    EXPIRED = 2
    CANCELLED = 3
    ERROR = 4


class TransactionStatus(int, ModelChoice):
    PENDING = 0
    SUCCESS = 1
    DECLINED = 2
    INVALID_MONEY_AMOUNT = 3
    INVOICE_EXPIRED = 4
    ERROR = 5


class TransactionType(int, ModelChoice):
    DUMMY = 0
    WALLETONE = 1


class Invoice(models.Model):
    total = models.DecimalField(_('total'), max_digits=11, decimal_places=2)
    captured_total = models.DecimalField(_('captured total'), max_digits=11, decimal_places=2, null=True, blank=True)
    expires_at = models.DateTimeField(_('expires at'), null=True, blank=True)
    success_transaction = models.ForeignKey(to='payment_gateway.Transaction', on_delete=models.SET_NULL, null=True,
                                            blank=True, verbose_name=_('transaction'), related_name='success_invoice')
    success_callback = models.CharField(_('success callback'), max_length=128)
    fail_callback = models.CharField(_('fail callback'), max_length=128, null=True, blank=True)
    status = models.PositiveSmallIntegerField(_('status'), choices=InvoiceStatus.choices())
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    modified_at = models.DateTimeField(_('modified at'), auto_now=True)
    details = JSONField(_('details'), null=True, blank=True, default=dict)

    class Meta:
        verbose_name = _('invoice')
        verbose_name_plural = _('invoices')


class Transaction(models.Model):
    invoice = models.ForeignKey(to='payment_gateway.Invoice', on_delete=models.CASCADE, related_name='transactions',
                                verbose_name=_('invoice'))
    money_amount = models.DecimalField(_('money amount'), max_digits=11, decimal_places=2)
    type = models.PositiveSmallIntegerField(_('type'), choices=TransactionType.choices())
    status = models.PositiveSmallIntegerField(_('status'), choices=TransactionStatus.choices())
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    modified_at = models.DateTimeField(_('modified at'), auto_now=True)

    class Meta:
        verbose_name = _('transaction')
        verbose_name_plural = _('transactions')


class InvoiceStatusChange(models.Model):
    invoice = models.ForeignKey('payment_gateway.Invoice', on_delete=models.CASCADE, verbose_name=_('invoice'))
    from_status = models.PositiveSmallIntegerField(_('from status'), choices=InvoiceStatus.choices())
    to_status = models.PositiveSmallIntegerField(_('to status'), choices=InvoiceStatus.choices())
    created_at = models.DateTimeField(_('modified at'), auto_now_add=True)
    details = JSONField(_('details'), null=True, blank=True, default=dict)

    class Meta:
        verbose_name = _('invoice status change')
        verbose_name_plural = _('invoice status changes')


class TransactionStatusChange(models.Model):
    transaction = models.ForeignKey('payment_gateway.Transaction', on_delete=models.CASCADE, verbose_name=_('transaction'))
    from_status = models.PositiveSmallIntegerField(_('from status'), choices=TransactionStatus.choices())
    to_status = models.PositiveSmallIntegerField(_('to status'), choices=TransactionStatus.choices())
    created_at = models.DateTimeField(_('modified at'), auto_now_add=True)
    details = JSONField(_('details'), null=True, blank=True, default=dict)

    class Meta:
        verbose_name = _('transaction status change')
        verbose_name_plural = _('transaction status changes')


class WalletOneTransaction(Transaction):
    transaction = models.OneToOneField('payment_gateway.Transaction', on_delete=models.CASCADE, parent_link=True)
    WMI_ORDER_ID = models.CharField(max_length=255, unique=True)
    WMI_MERCHANT_ID = models.CharField(max_length=255)
    WMI_PAYMENT_AMOUNT = models.DecimalField(max_digits=10, decimal_places=2)
    WMI_COMMISSION_AMOUNT = models.DecimalField(max_digits=10, decimal_places=2)
    WMI_CURRENCY_ID = models.IntegerField()
    WMI_TO_USER_ID = models.CharField(max_length=255, null=True)
    WMI_PAYMENT_NO = models.CharField(max_length=255)
    WMI_DESCRIPTION = models.CharField(max_length=255, null=True)
    WMI_SUCCESS_URL = models.URLField(blank=True)
    WMI_FAIL_URL = models.URLField(blank=True)
    WMI_EXPIRED_DATE = models.DateTimeField()
    WMI_CREATE_DATE = models.DateTimeField()
    WMI_UPDATE_DATE = models.DateTimeField()
    WMI_ORDER_STATE = models.CharField(max_length=255)
    WMI_NOTIFY_COUNT = models.IntegerField(null=True)
    WMI_EXTERNAL_ACCOUNT_ID = models.CharField(max_length=50, null=True)
    WMI_AUTO_ACCEPT = models.CharField(max_length=10)
    WMI_LAST_NOTIFY_DATE = models.DateTimeField(null=True)
    WMI_INVOICE_OPERATIONS = models.TextField(null=True)
    WMI_PAYMENT_TYPE = models.CharField(max_length=100)

    class Meta:
        verbose_name = _('walletone transaction')
        verbose_name_plural = _('walletone transactions')
