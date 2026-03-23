from rest_framework.exceptions import APIException


class InsufficientBalance(APIException):
    status_code = 400
    default_detail = "Insufficient wallet balance"
    default_code = "insufficient_balance"


class PaymentAlreadyProcessed(APIException):
    status_code = 409
    default_detail = "Payment already processed"
    default_code = "payment_duplicate"


class InvalidPaymentAmount(APIException):
    status_code = 400
    default_detail = "Payment amount must be greater than zero"
    default_code = "invalid_payment_amount"


class InvalidWalletTransactionAmount(APIException):
    status_code = 400
    default_detail = "Wallet transaction amount must be greater than zero"
    default_code = "invalid_wallet_transaction_amount"


class SelfPaymentNotAllowed(APIException):
    status_code = 400
    default_detail = "You cannot send money to yourself"
    default_code = "self_payment_not_allowed"


class WalletNotFound(APIException):
    status_code = 404
    default_detail = "Wallet not found"
    default_code = "wallet_not_found"


class PaymentRequestActionNotAllowed(APIException):
    status_code = 403
    default_detail = "You are not allowed to act on this payment request"
    default_code = "payment_request_action_not_allowed"


class PaymentRequestAlreadyResolved(APIException):
    status_code = 400
    default_detail = "Payment request is no longer pending"
    default_code = "payment_request_already_resolved"


class WalletTransactionNotPending(APIException):
    status_code = 400
    default_detail = "Wallet transaction is no longer pending"
    default_code = "wallet_transaction_not_pending"


class InvalidWalletTransactionOperation(APIException):
    status_code = 400
    default_detail = "Invalid wallet transaction operation"
    default_code = "invalid_wallet_transaction_operation"