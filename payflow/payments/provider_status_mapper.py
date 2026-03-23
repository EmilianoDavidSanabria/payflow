MERCADOPAGO_STATUS_MAP = {
    "approved": "COMPLETED",
    "rejected": "FAILED",
    "cancelled": "FAILED",
    "refunded": "FAILED",
    "charged_back": "FAILED",
    "pending": "PENDING",
    "in_process": "PENDING",
    "authorized": "PENDING",
}

def map_mercadopago_status(status):

    return MERCADOPAGO_STATUS_MAP.get(status, "PENDING")