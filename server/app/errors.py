"""业务异常（路由层映射 HTTP 状态码）"""


class BusinessError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status
