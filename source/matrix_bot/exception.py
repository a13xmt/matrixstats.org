class MatrixBotException(Exception):
    pass

class ClientError(MatrixBotException):
    pass

class RecaptchaError(ClientError):
    pass

class UserActionRequired(MatrixBotException):
    pass

class AuthError(MatrixBotException):
    pass
