from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import NotFound

from .models import Wallet
from .serializers import WalletSerializer


class WalletView(RetrieveAPIView):
    serializer_class = WalletSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        try:
            return self.request.user.wallet
        except Wallet.DoesNotExist:
            raise NotFound("Wallet not found for this user")