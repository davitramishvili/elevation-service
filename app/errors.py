"""Domain errors with a stable error code and HTTP status per failure mode."""


class ServiceError(Exception):
    status_code = 500
    code = "INTERNAL_ERROR"

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class InvalidAddressError(ServiceError):
    status_code = 400
    code = "INVALID_ADDRESS"


class AddressNotFoundError(ServiceError):
    status_code = 404
    code = "ADDRESS_NOT_FOUND"


class OutsideCoverageError(ServiceError):
    status_code = 422
    code = "OUTSIDE_COVERAGE"


class UpstreamServiceError(ServiceError):
    status_code = 502
    code = "UPSTREAM_ERROR"


class UpstreamTimeoutError(UpstreamServiceError):
    status_code = 504
    code = "UPSTREAM_TIMEOUT"
