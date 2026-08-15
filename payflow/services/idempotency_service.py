from django.db import IntegrityError, transaction

from idempotency.models import IdempotencyKey


class IdempotencyKeyInProgress(Exception):
    """
    Se levanta cuando otra request con la misma (user, key) todavía está
    procesándose (o quedó a medias por un crash) y por lo tanto no hay
    todavía una respuesta terminal para devolver.

    A propósito NO se resuelve automáticamente borrando el registro: una
    operación PROCESSING puede ya haber tenido efectos financieros (por
    ejemplo, el proceso murió después de mover el dinero pero antes de
    guardar la respuesta). Reintentar ciegamente podría duplicar esa
    operación. El caller debe devolver 409 y pedir al cliente que
    reintente más tarde; la resolución de un PROCESSING realmente
    huérfano es una decisión operativa, no automática.
    """
    pass


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
        """
        Lookup rápido y de solo lectura, filtrado SIEMPRE por usuario:
        la misma key usada por otro usuario nunca puede devolver esta
        respuesta. No es la garantía de concurrencia (esa la da
        create_record vía la unique constraint (user, key) + IntegrityError),
        es solo un atajo para no re-ejecutar create_record en el caso común
        de un reintento posterior a que la operación ya terminó.
        """
        record = IdempotencyKey.objects.filter(user=user, key=key).first()

        if not record:
            return None

        IdempotencyService._validate_request_identity(
            record=record,
            request_path=request_path,
            request_method=request_method,
        )

        if record.status == IdempotencyKey.STATUS_PROCESSING:
            return None

        if record.response_code is not None and record.response_body is not None:
            return record.response_body, record.response_code

        return None

    @staticmethod
    def create_record(user, key, request_path, request_method):
        """
        Intenta reservar la (user, key) para esta request y devuelve
        (record, is_new).

        - is_new=True: esta request ganó la carrera. Es dueña de ejecutar
          la operación de negocio y luego DEBE llamar a save_response (si
          terminó, ok o con error determinístico) o discard_record (si
          fue un error transitorio).
        - is_new=False: ya existía un registro para esa (user, key), sea
          porque:
            a) otra request concurrente ganó la carrera y ya terminó
               (record.status es COMPLETED o FAILED) -> el caller debe
               devolver record.response_body/response_code tal cual, SIN
               volver a ejecutar la operación.
            b) otra request sigue procesando ahora mismo, o quedó a medias
               (record.status == PROCESSING) -> se levanta
               IdempotencyKeyInProgress.

        La garantía de "solo una gana" no depende de locks de Python: se
        apoya en la unique constraint (user, key) de la base de datos. El
        INSERT de la request perdedora se bloquea a nivel de motor hasta
        que la ganadora hace commit, y recién ahí falla con IntegrityError
        -- por lo que, salvo un crash real de proceso a mitad de camino,
        cuando la perdedora reacciona ya va a encontrar el registro en un
        estado terminal, no en PROCESSING.
        """
        try:
            # El create() va en su propio savepoint: si falla por la
            # unique constraint, solo se revierte esta operación puntual
            # y la transacción que la envuelve (la de la vista, o la del
            # test) sigue utilizable para las queries que vienen después
            # (el SELECT de la rama except, y todo lo que haga el caller).
            with transaction.atomic():
                record = IdempotencyKey.objects.create(
                    user=user,
                    key=key,
                    request_path=request_path,
                    request_method=request_method,
                    status=IdempotencyKey.STATUS_PROCESSING,
                )
            return record, True
        except IntegrityError:
            record = IdempotencyKey.objects.get(user=user, key=key)

            IdempotencyService._validate_request_identity(
                record=record,
                request_path=request_path,
                request_method=request_method,
            )

            if record.status == IdempotencyKey.STATUS_PROCESSING:
                raise IdempotencyKeyInProgress()

            return record, False

    @staticmethod
    def save_response(record, response_body, status_code):
        """
        Guarda la respuesta terminal. El status se deriva del código HTTP:
        2xx/3xx -> COMPLETED, 4xx/5xx -> FAILED (fallo determinístico de
        negocio, cacheable). Los fallos transitorios nunca pasan por acá:
        usan discard_record en su lugar.
        """
        record.response_body = response_body
        record.response_code = status_code
        record.status = (
            IdempotencyKey.STATUS_COMPLETED
            if status_code < 400
            else IdempotencyKey.STATUS_FAILED
        )
        record.save(update_fields=["response_body", "response_code", "status", "updated_at"])

    @staticmethod
    def discard_record(record):
        """
        Usar cuando la operación falló por una razón inesperada/transitoria
        (bug, timeout, error de infraestructura) y NO por una regla de
        negocio determinística. Borra el registro para que un reintento
        legítimo con la misma Idempotency-Key vuelva a procesarse de cero,
        en vez de recibir para siempre una respuesta de error cacheada.

        IMPORTANTE: esto solo es seguro porque discard_record se llama
        exclusivamente en la rama de "la operación de negocio nunca llegó
        a tener efectos financieros" (ver los call sites). Si la operación
        ya movió dinero, el código debe usar save_response con el
        resultado real, nunca discard_record.
        """
        try:
            record.delete()
        except IntegrityError:
            pass