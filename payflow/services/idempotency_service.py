from idempotency.models import IdempotencyKey


class IdempotencyService:
    CONFLICT_MESSAGE = "Idempotency key already used for a different request"

    @staticmethod
    def _validate_request_identity(record, request_path, request_method):
        if (
            record.request_path != request_path
            or record.request_method != request_method
        ):
            raise ValueError(IdempotencyService.CONFLICT_MESSAGE)

    @staticmethod
    def get_existing_response(user, key, request_path, request_method):
        record = IdempotencyKey.objects.filter(key=key).first()

        if not record:
            return None

        IdempotencyService._validate_request_identity(
            record=record,
            request_path=request_path,
            request_method=request_method,
        )

        if record.response_code and record.response_body is not None:
            return record.response_body, record.response_code

        return None

    @staticmethod
    def create_record(user, key, request_path, request_method):
        record, created = IdempotencyKey.objects.get_or_create(
            key=key,
            defaults={
                "request_path": request_path,
                "request_method": request_method,
                "response_code": 0,
                "response_body": {},
            },
        )

        if not created:
            IdempotencyService._validate_request_identity(
                record=record,
                request_path=request_path,
                request_method=request_method,
            )

        return record

    @staticmethod
    def save_response(record, response_body, status_code):
        record.response_body = response_body
        record.response_code = status_code
        record.save(update_fields=["response_body", "response_code"])