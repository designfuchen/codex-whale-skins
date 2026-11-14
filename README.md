# 鲸娘皮肤工坊 · Whale Skins

把你的角色做成 Codex 原生桌宠。工作、需要输入、完成待查看和出错状态由 Codex 自己驱动；这个插件负责制作、校验和安装皮肤。

插件包含三个工作流：安装与检查、根据角色图制作原生动作、导入已有皮肤。支持原生 PNG/WebP 动作表、宠物目录和 ZIP。角色单图或普通 GIF 应作为制作参考，不能直接替代完整原生动作表。

## 在 Codex 中安装

```bash
codex plugin marketplace add https://github.com/designfuchen/codex-whale-skins.git
codex plugin add whale-skins@whale-skins
```

在插件页运行设置工作流，或在 Codex 中要求“用鲸娘皮肤工坊安装并检查我的桌宠”。本地插件更新后的可见时机取决于客户端；必要时在当前任务结束后重启桌面应用。

安装原生皮肤后，在 Settings > Pets 刷新并选择角色，再用 `/pet` 显示桌宠。插件会区分文件安装成功、角色被选中和实际显示成功，不会把这些状态混为一谈。原生桌宠行为见 [官方说明](https://learn.chatgpt.com/docs/pets)。

## 命令行工具

需要 Python 3.10+ 和 Pillow。Codex 桌面工作流优先使用其自带运行环境。

```bash
python -m pip install -e .
whale-skins validate /path/to/pet-package
whale-skins install /path/to/pet-package
whale-skins doctor
```

也可以直接运行 `plugins/whale-skins/scripts/skin_manager.py`。测试安装可指定 `--codex-home /tmp/my-test-codex`。默认遵循 `CODEX_HOME`，否则使用 `~/.codex`。重名且内容不同的皮肤默认不覆盖；明确重装时使用 `--replace`，旧包会先备份到 `pet-skin-backups`。

## 原生动作格式

新皮肤使用 v2：1536×2288，8 列、11 行，每格 192×208。九组标准动作是 idle、running-right、running-left、waving、jumping、failed、waiting、running 和 review，另有十六个顺时针视线方向。v2 的第 0 行第 6 列是 neutral-look 帧。

`running` 表示任务工作或处理，`running-right/left` 表示拖动时的方向运动。等待手势、工作动作和完成后的 review 应能清楚区分。动作生成采用内置 imagegen；代码只做确定性的提取、布局与检查。

插件附带 OpenAI hatch-pet 参考流水线，并修正了两个布局问题：为跳跃保留垂直位移和统一身体高度；保持已确认 neutral 格的基线。原始代码许可、修改说明和视觉验收规则一并保留。生成完成后应检查实际动画与十六个方向，结构验证通过不能替代视觉验收。

## 测试

```bash
python -m unittest discover -s tests -v
```

测试覆盖原生网格、保留 neutral 格、透明背景、空帧、ZIP 越界、源文件保留、重装备份、重复安装、跳跃位移与 neutral 注册。测试使用明确的合成几何像素，不把它们当作宠物素材。

GitHub Actions 配置保存在 `ci/github-actions-template.yml`。仓库创建时的授权不含 workflow scope，因此没有自动启用；需要 CI 时可由有相应权限的维护者放入 `.github/workflows/test.yml`。

## 数据和授权

工具只处理用户提供的皮肤文件与原生 pets 目录，不读取聊天内容或账号密钥。插件本身不运行日志监控进程，也不接管任务审批。真实状态、浮层和活动托盘由桌面客户端提供。

原创插件代码采用 [MIT](LICENSE)。附带的 OpenAI hatch-pet 代码采用其原有 Apache-2.0，见 [NOTICE](NOTICE)。用户角色图与第三方素材的授权独立于代码许可。

当前 Lanlan 鲸娘概念素材单独用于本机试用，没有混入公共源码仓库。你可以用自己的原创或获授权角色图制作、安装和分享皮肤。这个项目与 OpenAI、DeepSeek 均无官方关系。
