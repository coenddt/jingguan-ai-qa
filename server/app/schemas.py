"""跨路由共享 DTO 的补充声明（多数 DTO 就近定义在路由文件，此处集中导出）"""

from app.routers.qa import AskIn, SessionIn, SessionPatch  # noqa: F401
