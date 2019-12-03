from rest_framework import serializers

from payment_gateway.models import WalletOneTransaction, Invoice, TransactionType
from payment_gateway.walletone.provider import get_walletone_provider
from .dto import WalletOneTransaction as WalletOneTransactionDTO


class WalletOneSignSerializer(serializers.Serializer):
    provider = get_walletone_provider()

    invoice = serializers.PrimaryKeyRelatedField(queryset=Invoice.objects.all(), write_only=True)
    WMI_MERCHANT_ID = serializers.CharField(read_only=True)
    WMI_CURRENCY_ID = serializers.IntegerField(read_only=True)
    WMI_PAYMENT_AMOUNT = serializers.DecimalField(decimal_places=2, max_digits=20, read_only=True)
    WMI_DESCRIPTION = serializers.CharField(read_only=True)
    WMI_SUCCESS_URL = serializers.CharField(read_only=True)
    WMI_FAIL_URL = serializers.CharField(read_only=True)
    WMI_SIGNATURE = serializers.CharField(read_only=True)
    WMI_PAYMENT_NO = serializers.IntegerField(read_only=True)
    WMI_EXPIRED_DATE = serializers.CharField(read_only=True, max_length=100)

    def validate_invoice(self, invoice):
        self.provider.payment_handler.validate_status_for_pay(invoice, raise_exc=True)
        self.provider.payment_handler.validate_expiration(invoice, raise_exc=True)
        return invoice

    def create(self, validated_data):
        return self.provider.make_signed_invoice(validated_data['invoice'])


class WalletOneConfirmSerializer(serializers.ModelSerializer):
    provider = get_walletone_provider()

    WMI_SIGNATURE = serializers.CharField(max_length=28)
    WMI_TEST_MODE_INVOICE = serializers.CharField(max_length=1, required=False)

    class Meta:
        model = WalletOneTransaction
        fields = (
            'WMI_ORDER_ID',
            'WMI_MERCHANT_ID',
            'WMI_PAYMENT_AMOUNT',
            'WMI_COMMISSION_AMOUNT',
            'WMI_CURRENCY_ID',
            'WMI_TO_USER_ID',
            'WMI_PAYMENT_NO',
            'WMI_DESCRIPTION',
            'WMI_SUCCESS_URL',
            'WMI_FAIL_URL',
            'WMI_EXPIRED_DATE',
            'WMI_CREATE_DATE',
            'WMI_UPDATE_DATE',
            'WMI_ORDER_STATE',
            'WMI_SIGNATURE',
            'WMI_NOTIFY_COUNT',
            'WMI_EXTERNAL_ACCOUNT_ID',
            'WMI_AUTO_ACCEPT',
            'WMI_LAST_NOTIFY_DATE',
            'WMI_INVOICE_OPERATIONS',
            'WMI_PAYMENT_TYPE',
            'WMI_TEST_MODE_INVOICE'
        )
        extra_kwargs = {'WMI_ORDER_ID': {'validators': []}}

    def validate_WMI_PAYMENT_NO(self, WMI_PAYMENT_NO):
        if not Invoice.objects.filter(id=WMI_PAYMENT_NO).exists():
            raise serializers.ValidationError('', code='invalid_invoice')
        return WMI_PAYMENT_NO

    def validate(self, attrs):
        self.provider.validate_signature(attrs)
        del attrs['WMI_SIGNATURE']
        if 'WMI_TEST_MODE_INVOICE' in attrs:
            del attrs['WMI_TEST_MODE_INVOICE']
        return attrs

    def create(self, validated_data):
        data = WalletOneTransactionDTO(type=TransactionType.WALLETONE, invoice_id=validated_data['WMI_PAYMENT_NO'],
                                       money_amount=validated_data['WMI_PAYMENT_AMOUNT'], **validated_data)
        return self.provider.try_pay(data.invoice_id, data)
