"""分析过程 5 步中间产物收集（纯容器，禁 IO）"""

import time


class StepTracker:
    STEPS = ('理解问题', '生成查询', '安全校验', '执行取数', '生成结论')

    def __init__(self) -> None:
        self._last = time.time()
        self.items: list[dict] = [
            {'title': t, 'desc': '', 'done': False, 'ts': 0, 'elapsed': 0} for t in self.STEPS
        ]

    def _mark(self, idx: int) -> None:
        """记录步完成/失败时间戳（unix 毫秒）与自上一步以来的耗时（毫秒）"""
        now = time.time()
        self.items[idx]['ts'] = int(now * 1000)
        self.items[idx]['elapsed'] = round((now - self._last) * 1000)
        self._last = now

    def done(self, idx: int, desc: str) -> None:
        self.items[idx]['desc'] = desc
        self.items[idx]['done'] = True
        self._mark(idx)

    def fail(self, idx: int, desc: str) -> None:
        self.items[idx]['desc'] = desc
        self._mark(idx)

    def out(self) -> list[dict]:
        return self.items
