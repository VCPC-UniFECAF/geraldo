class DeliveryError(Exception):
    status_code = 400


class UnknownLocation(DeliveryError):
    status_code = 422


class UnknownItem(DeliveryError):
    status_code = 422


class SameLocation(DeliveryError):
    status_code = 422


class InsufficientStock(DeliveryError):
    status_code = 409


class NotFound(DeliveryError):
    status_code = 404


class NotAllowed(DeliveryError):
    status_code = 403


class InvalidState(DeliveryError):
    status_code = 409
