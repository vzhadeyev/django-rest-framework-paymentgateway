from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from payment_gateway.walletone.provider import WalletOneException
from .serializers import WalletOneConfirmSerializer, WalletOneSignSerializer


class WalletOneSignAPIView(GenericAPIView):
    serializer_class = WalletOneSignSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.save()
        return Response(data=data, status=status.HTTP_200_OK)


class WalletOneConfirmAPIView(GenericAPIView):
    serializer_class = WalletOneConfirmSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=False)
        if serializer.errors:
            return Response('WMI_SIGNATURE error', status=status.HTTP_400_BAD_REQUEST)
        try:
            serializer.save()
        except WalletOneException as e:
            return Response(e.error_msg, status=status.HTTP_400_BAD_REQUEST)
        return Response('WMI_RESULT=OK', status=status.HTTP_200_OK)


