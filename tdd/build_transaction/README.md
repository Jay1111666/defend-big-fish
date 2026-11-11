**保卫大肥鱼的 TDD 展示——建塔交易与异常输入校验**

作业说明第 2 页要求选择至少一个核心功能，先定义行为和编写测试，展示 Red → Green → Refactor，并保留测试代码、运行结果和开发记录。第 3 页要求提交相应的测试代码和必要记录。

本记录展示在已有建塔功能上，以 TDD 增强异常输入校验的实际开发过程。基础建塔早于本次测试存在。本次新增的行为是安全拒绝异常类型，并验证失败操作不会扣金币或增加炮塔。下面记录的 Red、Green 和 Refactor 均实际执行，三阶段使用同一份测试文件。

可选的核心功能如下。

| 功能 | 适合测试的业务规则 | 本项目中的用途 |
| --- | --- | --- |
| 建塔交易 | 合法空地、余额恰好够、差一金币、重复建造、非法参数、失败无副作用 | 本次完整演示 |
| 星星溅射 | 主目标只结算一次直击，周围目标各受一次溅射，半径边界和死亡处理正确 | 范围计算的进阶案例 |
| 月亮与风扇减速 | 月亮优先，两种减速不相乘，各自到期后恢复正确速度 | 时间与状态的进阶案例 |
| 波次与胜负 | 十关第五波均为对应的纯团子波，漏怪扣血，最终 Boss 存活时不能获胜 | 关卡规则验证 |
| 首通星声 | 首次通过才发奖励，重复结算与重新打开存档均不会重复领取 | 持久化与幂等性验证 |

这些功能在现有项目中已有不同程度的实现和测试。已有的通过结果可作为回归依据。若要把其他功能也作为新的 TDD 案例，应先提出尚未实现的行为，再记录测试与实现的顺序。

**1. 先明确本次功能契约**

建塔成功必须同时满足游戏允许操作、塔类型存在、目标格可建造和金币足够。成功返回 True，准确扣除一次费用，创建一座位于目标格的一级塔。

失败返回 False，金币和已有炮塔列表保持原状。异常参数属于业务拒绝范围，例如塔类型为列表或字典、格子编号为字符串或布尔值。格子编号约定为内置 int 类型，并处于有效编号范围内。布尔值虽然是 Python 中 int 的子类，仍应作为错误输入拒绝。

这组规则验证单次建塔调用的业务状态一致性。游戏循环在主线程处理操作，本例没有引入并发建塔协议。

**2. 先写测试**

测试位于 [tests/test_build_tdd.py](../../tests/test_build_tdd.py)，使用 Python 标准库 unittest，直接调用 Game，避免把测试依赖绑定到窗口坐标和美术效果。

| 测试 | 输入或场景 | 预期结果 |
| --- | --- | --- |
| 成功购买 | 空格、瓶子炮、余额足够 | 返回 True，扣一次费用，增加一座塔 |
| 金币下边界 | 余额等于价格 | 成功，余额为 0 |
| 金币不足 | 余额比价格少 1 | 返回 False，状态不变 |
| 禁止建造区域 | 路径、障碍物、守护角色区域 | 返回 False，状态不变 |
| 重复点击 | 对同一已占用格再次购买 | 第二次失败，不重复扣款 |
| 异常塔类型 | 不存在的名称、空字符串、None、整数、布尔值、列表、字典 | 安全拒绝，状态不变 |
| 异常格子编号 | -1、格子总数、None、字符串、浮点数、列表、字典、布尔值 | 不能选作可建造格，购买失败，状态不变 |
| 对局结束 | 胜利或失败状态 | 拒绝购买，状态不变 |

每次断言失败购买时，还同时比较调用前后的金币和炮塔列表。仅检查返回值可能漏掉“返回 False 但已经扣钱”的错误。

余额边界的实际测试片段如下。

```python
def test_exact_balance_can_purchase_and_ends_at_zero(self):
    self.game.coins = self.cost
    self.assertTrue(self.game.build('bottle', self.pad))
    self.assertEqual(self.game.coins, 0)
    self.assertEqual(len(self.game.towers), 1)
```

**3. Red——在修改 model.py 前运行测试**

运行命令如下。

```powershell
.\.venv\Scripts\python.exe -B -m unittest -v tests.test_build_tdd
```

实际结果如下。

```text
Ran 8 tests
FAILED (failures=1, errors=2)
```

失败来自三个子用例。

- can_build(False) 返回 True。False 被当作编号 0，违反本次明确的编号类型契约。
- build([], 0) 触发 TypeError，列表不可哈希。
- build({}, 0) 同样触发 TypeError，字典不可哈希。

其他正常行为和边界测试已经通过，因此测试指出的是尚未满足的新契约。此次失败没有依靠破坏已有代码或伪造输出。

原始控制台输出保存在 [01-red.txt](01-red.txt)。

**4. Green——增加最小校验**

先在 can_build 中增加布尔值拒绝分支，在 build 查询塔类型字典之前检查参数是否为字符串。

```python
# can_build 的新增入口校验
if isinstance(pad, bool):
    return False

# build 的新增入口校验
if not isinstance(kind, str):
    return False
```

这两处校验放在扣金币和创建炮塔之前。再次运行同一测试文件，实际结果如下。

```text
Ran 8 tests
OK
```

完整输出保存在 [02-green.txt](02-green.txt)，相对 Red 版本的代码变化保存在 [02-green.patch](02-green.patch)。

**5. Refactor——合并入口判断**

Green 阶段的布尔值判断与整数判断有重复。本次契约明确要求内置整数，因此将两次类型判断合并。

```python
if type(pad) is not int or not 0 <= pad < len(PADS):
    return False
```

塔类型校验也并入已有的失败条件，保持所有验证先于状态修改。最终 build 方法如下。

```python
def build(self, kind, pad):
    if (self.state != 'playing' or not isinstance(kind, str)
            or kind not in TOWERS or not self.can_build(pad)
            or self.coins < TOWERS[kind]['cost']):
        return False
    self.coins -= TOWERS[kind]['cost']
    self.towers.append(Tower(kind, pad))
    return True
```

短路求值保证非字符串参数在字典查询之前被拒绝。再次运行原来的 8 项测试，结果仍为 OK。

本次重构减少了重复判断和独立返回分支，沿用现有 Game、Tower 与 TOWERS。输出保存在 [03-refactor.txt](03-refactor.txt)，代码变化保存在 [03-refactor.patch](03-refactor.patch)。

之后执行完整回归命令，验证其他炮塔、波次、音效、角色购买和存档行为。

```powershell
.\.venv\Scripts\python.exe -B -m unittest -v
```

实际结果为 70 项测试全部通过，包括原有的 62 项测试和本次新增的 8 项专项测试。完整结果见 [04-regression.txt](04-regression.txt)。

**6. 如何在课程设计报告中展示**

报告的“测试驱动开发与验证”部分可以按“功能契约与用例表 → Red 的三条失败原因 → Green 的最小改动 → Refactor 的整理 → 回归结果”编排，并引用本目录的真实日志和补丁。测试文件由 tests 包组织，可随源码一起提交。

日志记录了执行时间、命令、退出码、model.py 与测试文件的 SHA256。三阶段测试文件哈希一致，可核对测试是否在实现之后被修改。02-green.patch 和 03-refactor.patch 可以追踪两次代码变化。时间和哈希作为过程记录，课程报告还应解释测试设计和代码行为。

如需现场复演，可在项目副本中先反向应用 03-refactor.patch，再反向应用 02-green.patch，还原 Red 版本。运行专项测试观察失败后，正向应用 02-green.patch 得到 Green，再正向应用 03-refactor.patch 得到重构版本。每步都运行同一专项测试命令。补丁可使用 git apply 及其 --reverse 参数应用。

本次 AI 协作内容包括功能候选分析、测试编写、运行验证、修复和重构。报告中对学生独立判断的描述应由本人根据实际参与情况填写。答辩时应能解释布尔值与整数的关系、边界测试的意义，以及为何所有拒绝条件应在扣款之前检查。
