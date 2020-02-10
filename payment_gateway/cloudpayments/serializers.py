from payment_gateway.cloudpayments.provider import get_cloudpayments_provider, CloudPaymentsResultCode
from payment_gateway.models import TransactionType, Invoice
from rest_framework import serializers


class CloudPaymentsSerializerBase(serializers.Serializer):
    provider = get_cloudpayments_provider()

    TransactionId = serializers.IntegerField()
    Amount = serializers.DecimalField(max_digits=11, decimal_places=2)
    Currency = serializers.CharField()
    DateTime = serializers.DateTimeField()
    CardFirstSix = serializers.CharField(min_length=6, max_length=6)
    CardLastFour = serializers.CharField(min_length=4, max_length=4)
    CardType = serializers.CharField()
    CardExpDate = serializers.CharField()
    TestMode = serializers.BooleanField()
    Status = serializers.CharField()
    OperationType = serializers.CharField()
    InvoiceId = serializers.CharField()
    AccountId = serializers.CharField(required=False)
    SubscriptionId = serializers.CharField(required=False)
    TokenRecipient = serializers.CharField(required=False)
    Name = serializers.CharField(required=False)
    Email = serializers.EmailField(required=False)
    IpAddress = serializers.IPAddressField(required=False)
    IpCountry = serializers.CharField(required=False, max_length=2)
    IpCity = serializers.CharField(required=False)
    IpRegion = serializers.CharField(required=False)
    IpDistrict = serializers.CharField(required=False)
    Issuer = serializers.CharField(required=False)
    IssuerBankCountry = serializers.CharField(required=False, max_length=2)
    Description = serializers.CharField(required=False)
    Data = serializers.JSONField(required=False)


class CloudPaymentsCheckSerializer(CloudPaymentsSerializerBase):
    def create(self, validated_data):
        data = self.provider.transaction_handler.TransactionDTO(type=TransactionType.CLOUDPAYMENTS,
                                                                invoice_id=int(validated_data['InvoiceId']),
                                                                money_amount=validated_data['Amount'], **validated_data)
        return {'code': self.provider.check(data)}


class CloudPaymentsPaySerializer(CloudPaymentsSerializerBase):
    # Pay specific fields
    GatewayName = serializers.CharField(required=False)
    Token = serializers.CharField(required=False)
    TotalFee = serializers.DecimalField(max_digits=11, decimal_places=2)

    def create(self, validated_data):
        data = self.provider.transaction_handler.TransactionDTO(type=TransactionType.CLOUDPAYMENTS,
                                                                invoice_id=validated_data['InvoiceId'],
                                                                money_amount=validated_data['Amount'], **validated_data)
        self.provider.pay(data.invoice_id, data)
        return {'code': CloudPaymentsResultCode.OK}
