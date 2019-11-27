from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from .serializers import DummyTransactionSerializer


class DummyProviderAPIView(GenericAPIView):
    serializer_class = DummyTransactionSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        invoice = serializer.save()
        payload = {
            'invoice_id': invoice.id,
            'transaction_id': invoice.success_transaction_id,
            'status': invoice.status,
        }
        return Response(data=payload, status=status.HTTP_200_OK)
