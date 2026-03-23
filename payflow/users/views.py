from django.contrib.auth import get_user_model
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

User = get_user_model()


class UserSearchView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        query = request.GET.get("q", "")

        users = (
            User.objects
            .filter(username__icontains=query)
            .exclude(id=request.user.id)
            .order_by("username")[:10]
        )

        data = [
            {
                "id": user.id,
                "username": user.username
            }
            for user in users
        ]

        return Response(data)