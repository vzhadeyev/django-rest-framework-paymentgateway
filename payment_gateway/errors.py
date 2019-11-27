from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.exceptions import APIException


class PaymentError(APIException):
    default_code = 'payment_error'


class InvoiceExpired(PaymentError):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _('Invoice has expired.')
    default_code = 'invoice_expired'


class InvoiceAlreadyPaid(PaymentError):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _('Invoice has already been paid.')
    default_code = 'invoice_already_paid'


class InvoiceInvalidStatus(PaymentError):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _('Can not perform action with order current state.')
    default_code = 'invoice_invalid_state'


class InvalidMoneyAmount(PaymentError):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _('Invalid money amount.')
    default_code = 'invalid_money_amount'


class InsufficientMoneyAmount(InvalidMoneyAmount):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _('Insufficient money amount.')
    default_code = 'insufficient_money_amount'
