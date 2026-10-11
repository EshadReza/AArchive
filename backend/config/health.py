"""Public liveness endpoint. Dependency readiness is a separate future contract."""

from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    http_method_names = ["get", "head"]

    def get(self, request):
        return Response({"status": "ok"}, headers={"Cache-Control": "no-store"})
