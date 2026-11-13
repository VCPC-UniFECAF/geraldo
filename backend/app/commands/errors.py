from app.commands.create_delivery import DeliveryError


class NotFound(DeliveryError):
    status_code = 404


class NotAllowed(DeliveryError):
    status_code = 403


class InvalidState(DeliveryError):
    status_code = 409
