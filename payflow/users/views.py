from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from .serializers import UserRegisterSerializer, CurrentUserSerializer

User = get_user_model()


class UserRegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        response_serializer = CurrentUserSerializer(user)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = CurrentUserSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)


class UserSearchView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = request.GET.get("q", "").strip()

        users = (
            User.objects
            .filter(username__icontains=query)
            .exclude(id=request.user.id)
            .order_by("username")[:10]
        )

        data = [
            {
                "id": user.id,
                "username": user.username,
            }
            for user in users
        ]

        return Response(data, status=status.HTTP_200_OK)