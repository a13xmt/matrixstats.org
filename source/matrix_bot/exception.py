class MatrixBotException(Exception):
    pass

class ClientError(MatrixBotException):
    pass

class RecaptchaError(ClientError):
    pass

class TimeoutError(ClientError):
    pass

class HandlerNotImplemented(ClientError):
    pass

class UserActionRequired(MatrixBotException):
    pass

class ConfigurationError(MatrixBotException):
    pass

class AuthError(MatrixBotException):
    pass

class StopSync(MatrixBotException):
    pass
