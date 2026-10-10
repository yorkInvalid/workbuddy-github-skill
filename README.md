# workbuddy-github-skill

帮助 WorkBuddy 用户理解 GitHub 项目的用途和使用入口，主动补充影响使用决定的运行条件与限制。

**当前为 0.1.1 本地预览版本，尚未经 WorkBuddy 实机兼容验证，也未发布到技能市场。**

## 第一版能做什么

给出一个公开的 GitHub 仓库链接，Skill 获取有来源的资料，回答：

- 项目是什么，能帮助谁完成什么工作；
- 有没有在线服务、桌面安装包或明确的官方使用路径；
- 安装包、模型和源码分别需要什么运行条件；
- 累计关注度、最近发布，以及哪些热度信息尚未核实；
- 使用例子、费用、许可证和会影响使用决定的限制；
- 下一步该看哪里；如果 WorkBuddy 能为当前任务提供具体帮助，再给出有依据的建议。

需要判断当前电脑是否适用时，按需探测系统、版本和架构；只有相关时才读取内存和运行时信息。探测失败的字段保留为未知，不要求用户反复填写。

本版不实现 topic 搜索、Trending 榜单采集、期间 Stars 增长统计，也不安装或运行被分析的项目。Skill 提供资料分析和官方指引，不承诺第三方软件能够在用户电脑上运行。

## 使用示例

> 帮我看看这个项目有什么用：https://github.com/isair/jarvis

> 这个项目在我当前电脑上有什么已知限制？优先找官方安装包，说明中文能力和费用。

> 它现在有多少 Stars，最近有没有发布版本？如果查不到周榜排名，请直接说明。

用户不需要把分析维度逐项写进问题。Skill 先给出简短结论，主动补充具体例子、使用入口和关键条件，再按需展开。关键结论附官方资料链接和核查日期，区分文档说明、分析推断与尚未核实。

WorkBuddy 相关帮助属于内部按需判断：有具体价值时自然放入使用方法或下一步，区分辅助使用与直接接入，不固定生成关系章节。用户明确询问接入时再详细回答。

## 本地开发

脚本使用 Python 标准库，无需安装第三方包；需要可用的 Python 3.10+ 和访问 GitHub 的网络。普通 Skill 不保证托管 Python，必须先确认当前环境可执行。

在仓库根目录执行：

```bash
python3 --version
python3 skills/github-project-guide/scripts/github_data.py repo https://github.com/isair/jarvis
python3 skills/github-project-guide/scripts/system_info.py
```

只在分析确实需要时补充资料和详细系统字段：

```bash
python3 skills/github-project-guide/scripts/github_data.py repo https://github.com/isair/jarvis --doc docs/CONFIGURATION.md --issues
python3 skills/github-project-guide/scripts/system_info.py --details
```

`--doc` 可重复传入仓库内文档路径；只使用从仓库资料中实际发现的路径。`--issues` 返回的问题样本不能证明已经穷尽所有兼容性问题；已发现具体 Issue 编号时可用 `--issue 172` 定向读取，最多 5 个。脚本结果为 JSON，包含获取状态和来源信息；截断或失败不应解释成“没有限制”。如需保存结果，可使用 `github_data.py` 的 `--json-out` 参数指定新文件路径；父目录需要存在，脚本不会覆盖已有文件。

公开仓库可匿名查询，可能遇到 GitHub 限流。不要将访问令牌放入命令参数、报告或提交到仓库中。系统探测结果用于当前分析，不随 GitHub 查询上传。

```bash
python3 -m unittest discover -s tests
python3 scripts/build_skill.py
```

打包脚本生成 `dist/github-project-guide-0.1.1.zip`。测试时选择此版本；修改源文件后需要重新打包。如果之前已经导入旧版，须在客户端确认使用的是新版。正式提交前，仍需要在 WorkBuddy 中验证导入、调用、工具可用性、报告质量和失败处理。

## 目录

```text
skills/github-project-guide/   # 发布技能包
  SKILL.md                     # 触发方式与分析流程
  scripts/                     # GitHub 资料和系统信息获取
  references/                  # 判断规则、平台能力依据
  templates/                   # 报告结构
scripts/build_skill.py         # 校验并打包
tests/                        # 脚本测试和人工验收用例
docs/product-spec.md          # 产品范围与后续计划
```

测试与产品设计文档不进入技能包。仓库与技能的名称分别是 `workbuddy-github-skill` 和 `github-project-guide`。

## 验收与发布

先按照 [产品规格](docs/product-spec.md) 和 [Jarvis 验收用例](tests/cases/jarvis.md) 检查分析是否准确，再在实际 WorkBuddy 中导入 ZIP。开发者账号已注册；市场提交以开发者后台当时的字段和审核要求为准。能够打包不代表已经通过平台审核或客户端兼容验证。

后续再加入主题发现、候选筛选和独立的趋势数据获取。反馈问题时请提供输入、错误步骤和必要的版本信息，删除令牌、私人文件内容等敏感信息。

## 许可证

[MIT](LICENSE)。此许可证适用于本项目，不改变被分析的第三方项目或引用资料各自的许可条件。
