from django.contrib import admin
from .models import Invoice, InvoiceStatusChange, Transaction, TransactionStatusChange, WalletOneTransaction


class InvoiceStatusChangeInline(admin.TabularInline):
    model = InvoiceStatusChange
    extra = 0
    show_change_link = True
    can_delete = False
    fields = ('created_at', 'from_status', 'to_status', 'details')
    readonly_fields = ('from_status', 'to_status', 'details', 'created_at')


class TransactionInline(admin.TabularInline):
    model = Transaction
    extra = 0
    show_change_link = True
    can_delete = False
    fields = ('id', 'status', 'money_amount', 'type', 'created_at')
    readonly_fields = ('id', 'created_at', 'status', 'money_amount', 'type')


class InvoiceAdmin(admin.ModelAdmin):
    inlines = (InvoiceStatusChangeInline, TransactionInline)
    list_display = ('id', 'total', 'captured_total', 'status', 'created_at', 'expires_at', 'modified_at')
    list_per_page = 30
    raw_id_fields = ('success_transaction',)
    readonly_fields = ('created_at', 'modified_at')


class TransactionStatusChangeInline(admin.TabularInline):
    model = TransactionStatusChange
    extra = 0
    can_delete = False
    show_change_link = True
    fields = ('id', 'created_at', 'from_status', 'to_status', 'details')
    readonly_fields = ('details', 'created_at')


class WalletOneTransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'transaction',)
    list_per_page = 30
    raw_id_fields = ('transaction',)


class WalletOneTransactionInline(admin.TabularInline):
    model = WalletOneTransaction
    extra = 0
    can_delete = False
    show_change_link = True
    raw_id_fields = ('invoice',)


class TransactionAdmin(admin.ModelAdmin):
    inlines = (TransactionStatusChangeInline, WalletOneTransactionInline)
    list_display = ('id', 'invoice', 'money_amount', 'type', 'status', 'created_at', 'modified_at')
    list_per_page = 30
    raw_id_fields = ('invoice',)
    readonly_fields = ('created_at', 'modified_at')


admin.site.register(Invoice, InvoiceAdmin)
admin.site.register(Transaction, TransactionAdmin)
admin.site.register(WalletOneTransaction, WalletOneTransactionAdmin)
