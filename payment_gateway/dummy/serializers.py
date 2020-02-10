from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from payment_gateway.dummy.provider import get_dummy_provider
from payment_gateway.models import Invoice, TransactionType


class DummyTransactionSerializer(serializers.ModelSerializer):
    payment_provider = get_dummy_provider()

    invoice_id = serializers.IntegerField(write_only=True)
    money_amount = serializers.DecimalField(max_digits=11, decimal_places=2, write_only=True)

    def validate_invoice_id(self, invoice_id):
        if not Invoice.objects.filter(pk=invoice_id).exists():
            raise serializers.ValidationError(_('Invalid invoice identifier.'))
        return invoice_id

    class Meta:
        model = Invoice
        fields = ('invoice_id', 'money_amount')

    def create(self, validated_data):
        transaction_data = self.payment_provider.transaction_handler.TransactionDTO(TransactionType.DUMMY,
                                                                                    validated_data['invoice_id'],
                                                                                    validated_data['money_amount'])
        invoice, transaction = self.payment_provider.pay(validated_data['invoice_id'], transaction_data)
        return invoice
