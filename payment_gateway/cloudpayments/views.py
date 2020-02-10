import logging

from payment_gateway.cloudpayments.provider import NotificationValidator
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import BasePermission
from rest_framework.response import Response

from .serializers import CloudPaymentsCheckSerializer, CloudPaymentsPaySerializer

logger = logging.getLogger(__name__)


class NotificationPermission(BasePermission):
    validator = NotificationValidator()

    def has_permission(self, request, view):
        content_hmac = request.headers.get('Content-HMAC', None)
        content = request.body
        return content_hmac is not None and self.validator.validate(content, content_hmac)


class CloudPaymentsCheckAPIView(GenericAPIView):
    serializer_class = CloudPaymentsCheckSerializer
    permission_classes = (NotificationPermission,)

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.save()
        return Response(data=data, status=status.HTTP_200_OK)


class CloudPaymentsPayAPIView(GenericAPIView):
    serializer_class = CloudPaymentsPaySerializer
    permission_classes = (NotificationPermission,)

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.save()
        return Response(data, status=status.HTTP_200_OK)
