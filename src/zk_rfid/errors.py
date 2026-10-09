"""SDK exceptions; errors retain the native response and uncertain outcome."""


class ZKError(Exception):
    """Base SDK exception."""


class ValidationError(ZKError, ValueError):
    """Invalid input; no command was transmitted."""


class ProtocolError(ZKError):
    """Invalid or unsupported response layout."""


class UnsupportedFeature(ZKError):
    """Operation outside the reader/tag capability."""


class UnverifiedFeature(UnsupportedFeature):
    """Insufficient evidence to choose a wire format or conversion."""


class StateError(ZKError):
    """Operation conflicts with reader state."""


class TransportError(ZKError):
    """Connection failed; reader may already have changed."""


class ExchangeError(TransportError):
    """Incomplete exchange, retaining valid responses already received."""

    def __init__(self, message, *, frames=(), transmitted=False):
        super().__init__(message)
        self.frames = tuple(frames)
        self.transmitted = transmitted


class RequestTimeout(ExchangeError, TimeoutError):
    """Host monotonic deadline expired (not a device status)."""


class QueueOverflow(ProtocolError):
    """Consumer could not keep up; loss is never silently hidden."""


class DeviceError(ZKError):
    def __init__(self, command, status, data=b"", tag_error=None):
        self.command, self.status, self.data, self.tag_error = command, status, data, tag_error
        super().__init__(
            f"ZK command 0x{command:02X}: status 0x{status:02X}"
            + (f", tag error 0x{tag_error:02X}" if tag_error is not None else "")
        )


class OperationError(ZKError):
    """Raised by require_success(), retaining the complete CommandResult."""

    def __init__(self, result):
        self.result = result
        super().__init__(f"Operation {result.outcome.value}: {'; '.join(result.diagnostics)}")
