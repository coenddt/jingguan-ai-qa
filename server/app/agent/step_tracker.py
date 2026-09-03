"""分析过程 5 步中间产物收集（纯容器，禁 IO）"""


class StepTracker:
    STEPS = ['理解问题', '生成查询', '安全校验', '执行取数', '生成结论']

    def __init__(self) -> None:
        self.items: list[dict] = [
            {'title': t, 'desc': '', 'done': False} for t in self.STEPS
        ]

    def done(self, idx: int, desc: str) -> None:
        self.items[idx]['desc'] = desc
        self.items[idx]['done'] = True

    def fail(self, idx: int, desc: str) -> None:
        self.items[idx]['desc'] = desc

    def out(self) -> list[dict]:
        return self.items
