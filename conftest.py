"""pytest 配置: 为未继承 unittest.TestCase 的测试类注入断言方法。

测试文件不可修改, 而其中的测试类直接调用 self.assertIsNotNone 等
unittest 断言, 因此在收集阶段把这些断言注入到普通测试类上。
"""

import unittest

_INJECTED_NAMES = tuple(
    name for name in dir(unittest.TestCase) if name.startswith("assert")
) + ("fail", "failureException", "_formatMessage", "_truncateMessage")


def _inject_asserts(cls):
    for name in _INJECTED_NAMES:
        if not hasattr(cls, name):
            setattr(cls, name, getattr(unittest.TestCase, name))


def pytest_collection_modifyitems(items):
    for item in items:
        cls = getattr(item, "cls", None)
        if isinstance(cls, type) and not issubclass(cls, unittest.TestCase):
            _inject_asserts(cls)
