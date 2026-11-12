# 浏览器构建与发布

Windows 下单独创建 `.venv-web`，避免将原桌面环境的 pygame 替换成 pygame-ce。

```powershell
py -3.13 -m venv .venv-web
.\.venv-web\Scripts\python.exe -m pip install -r requirements-web.txt
.\.venv-web\Scripts\python.exe -m unittest discover -v
.\.venv-web\Scripts\python.exe tools/build_web.py
.\.venv-web\Scripts\python.exe -m http.server 8000 --bind 127.0.0.1 --directory dist/web
```

浏览器打开 http://127.0.0.1:8000 ，不能直接双击 HTML 文件。首次加载要获取 Pygbag 的 Python/pygame-ce WebAssembly 运行环境；网页素材约数 MB，运行环境体积另计，需要稳定网络。发布到 GitHub Pages 后，玩家无需安装 Python。

之后也可以双击根目录 `start-web.bat` 启动预览。必须保持它的窗口打开；窗口关闭或服务进程退出时，会出现 `ERR_CONNECTION_REFUSED`。这表示本机服务未运行，需要重新启动预览。

## GitHub Pages

1. 提交并推送 `web-version` 分支后，Actions 会运行全部测试并构建 `browser-game` 附件，此时不会自动覆盖线上站点。
2. 仓库 Settings → Pages → Build and deployment → Source 选择 **GitHub Actions**。
3. 若希望直接发布测试分支，在 Actions 中打开 **Test and build browser game**，点击 Run workflow，选择 `web-version`。如环境部署规则只允许 main，需要在 github-pages 环境允许该分支。
4. 正式发布可以合并到 main，后续 main 的更新在测试通过后自动部署。
5. 仓库为 `Jay1111666/defend-big-fish` 时，预期地址是 https://jay1111666.github.io/defend-big-fish/ ，须等部署成功后才可使用。

流程失败时查看首个红色步骤的输出；不要把 `.venv-web`、`build`、`dist` 或玩家 `saves` 推入源码仓库。部署只上传 `dist/web`，不包含个人存档、测试过程或开发环境。

## 浏览器行为

已在隔离的 Edge 浏览器中验证加载、建塔、战斗与第十关选关；商店购买、角色选择和音乐设置在刷新后仍保留。手机横屏模拟的触摸购买只扣除一次货币。原有及新增 Python 测试合计 101 项通过。实际手机 Safari、微信内置浏览器还需分别实机验证。

电脑已安装 Edge 和 Node.js 时，可在预览服务运行期间复现端到端检查。所有操作使用独立测试浏览器，截图与日志写入忽略的 `build` 目录。

```powershell
npm install --prefix build/browser-tools --no-save playwright
node tools/browser_smoke.cjs
```

- 固定 1280×800 逻辑画布按屏幕等比例缩放，横屏更易操作；SDL 将缩放后的鼠标位置映射到逻辑坐标。
- 开始按钮在游戏准备完成后出现，点击后启用音乐与音效。
- 触摸使用 FINGERDOWN，忽略重复的触摸合成鼠标事件，另有取消选择按钮。
- 切换标签页/失去焦点会暂停活动波次，返回后手动继续，不补算后台时间。
- 桌面版保留 SQLite，网页版以同一存档接口使用 localStorage，购买和首通奖励立即保存。浏览器禁用存储或存档损坏时使用临时会话，并在开始页面和设置页说明。
- 浏览器存档按网站来源隔离，不与桌面 EXE 自动同步；换设备、清除网站数据、无痕会话关闭可能失去本地进度。多标签页的顺序读写可看到最新存档，但没有服务端级别的并发事务保证。
- Pygbag 打包目录使用白名单，PNG 使用调色板压缩、WAV 转 OGG。图片尺寸保持不变，以兼容图集坐标和 wasm 图片预加载。原始素材和桌面音频不变。

## 模板与字体来源

`game.tmpl` 改编自 pygame-web 官方 Pygbag 0.9.3 默认模板，来源 https://pygame-web.github.io/cdn/0.9.3/default.tmpl ，保留其运行引导代码，自定义中文加载界面与等比例画布样式。中文字体来源和许可见 `assets/fonts`。
