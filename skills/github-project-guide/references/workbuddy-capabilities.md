# WorkBuddy 能力依据

核查日期：2026-10-10。以下是设计依据，不是当前客户端实测结果。涉及新版本能力时重新核查官方来源与实际宿主工具。

| 官方能力 | 本 Skill 如何使用 | 不能由此推断 |
| --- | --- | --- |
| 技能包支持 SKILL.md、references、scripts、templates | 打包分析流程、获取脚本和资料 | 用户机器一定装有 Python |
| 技能脚本经 Bash 执行 | 有实际工具和运行时时执行本包脚本 | 普通 Skill 自动享有连接器运行时托管 |
| 连接器支持 MCP + Skill 与 CLI + Skill | 判断目标项目提供哪一种实际接口 | 任意仓库都能直接成为连接器 |
| MCP 服务有传输、认证等接入要求 | 核查项目是否提供服务及所需配置 | MCP 客户端可以被当成 MCP 服务调用 |
| 结果区可展示工作文件、文档和网页 | 有需要时输出用户可查看的报告文件 | 普通 Skill 自动获得上传、分享或发布 API |

官方来源：

- [技能开发](https://open.workbuddy.cn/docs/skill)：目录、必要元数据、脚本与资源用法。
- [连接器开发](https://open.workbuddy.cn/docs/connector)：MCP/CLI 两种方案、配置、运行时与认证。
- [结果查看](https://www.workbuddy.cn/docs/workbuddy/Results)：任务结果区、文件及网页预览。

这些能力必须结合宿主实际提供的工具使用。平台有某项产品能力不意味着每次 Skill 调用都得到对应工具、用户授权或外部账号权限。

当前包是普通 Skill，不包含 connector-meta.json、MCP 服务或 CLI 连接器配置。连接器文档中的安装、认证、运行时声明不能搬来作为本包的隐含保证。
