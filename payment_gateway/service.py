from datetime import datetime
from decimal import Decimal

from django.db import transaction

from .models import Invoice, InvoiceStatus, InvoiceStatusChange


def create_invoice(total: Decimal, success_callback: str, fail_callback: str = None,
                   expires_at: datetime = None, details: dict = None) -> Invoice:
    return Invoice.objects.create(total=total, expires_at=expires_at, success_callback=success_callback,
                                  fail_callback=fail_callback, status=InvoiceStatus.PENDING, details=details)


def cancel_invoice_by_id(invoice_id: int) -> Invoice:
    with transaction.atomic():
        invoice = Invoice.objects.select_for_update().get(pk=invoice_id)
        return cancel_invoice(invoice)


def cancel_invoice(invoice: Invoice) -> Invoice:
    assert transaction.get_connection().in_atomic_block
    _set_invoice_status(invoice, InvoiceStatus.CANCELLED)
    return invoice


def expire_invoice_by_id(invoice_id: int) -> Invoice:
    with transaction.atomic():
        invoice = Invoice.objects.select_for_update().get(pk=invoice_id)
        return expire_invoice(invoice)


def expire_invoice(invoice: Invoice) -> Invoice:
    assert transaction.get_connection().in_atomic_block
    _set_invoice_status(invoice, InvoiceStatus.EXPIRED)
    return invoice


def _set_invoice_status(invoice: Invoice, status: InvoiceStatus) -> Invoice:
    old_status = invoice.status
    invoice.status = status
    invoice.save()
    _write_invoice_history(invoice, old_status)
    return invoice


def _write_invoice_history(invoice: Invoice, old_status) -> InvoiceStatusChange:
    return InvoiceStatusChange.objects.create(
        invoice=invoice,
        from_status=old_status,
        to_status=invoice.status
    )
