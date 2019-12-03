import logging

from payment_gateway.walletone.provider import WalletOneException
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from .serializers import WalletOneConfirmSerializer, WalletOneSignSerializer

logger = logging.getLogger(__name__)


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
        try:
            serializer.is_valid(raise_exception=True)
            serializer.save()
        except WalletOneException as e:
            logger.info('Error processing W1 payment.', exc_info=True, extra=request.data)
            return Response(e.error_msg, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.info('Error processing W1 payment.', exc_info=True, extra=request.data)
            return Response('WMI_RESULT=RETRY', status=status.HTTP_400_BAD_REQUEST)
        return Response('WMI_RESULT=OK', status=status.HTTP_200_OK)
