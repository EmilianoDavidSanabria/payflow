import json

from django.http import JsonResponse

from idempotency.models import IdempotencyKey


def idempotent_endpoint(view_func):

    def wrapper(self, request, *args, **kwargs):

        key = request.headers.get("Idempotency-Key")

        if not key:
            return view_func(self, request, *args, **kwargs)

        existing = IdempotencyKey.objects.filter(key=key).first()

        if existing:
            return JsonResponse(
                existing.response_body,
                status=existing.response_code,
            )

        response = view_func(self, request, *args, **kwargs)

        try:
            body = json.loads(response.render().content)
        except Exception:
            body = {}

        IdempotencyKey.objects.create(
            key=key,
            request_path=request.path,
            request_method=request.method,
            response_code=response.status_code,
            response_body=body,
        )

        return response

    return wrapper