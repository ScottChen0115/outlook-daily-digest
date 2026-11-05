# 团队交接文档：Email Digest Agent 网页版

> **演示链接：https://email-digest-agent-eo4s.onrender.com**（闲置后第一次打开可能要等 1 分钟）
> 截止时间：**11 月 8 日（周日）23:59**，在 FeedbackFruits 提交。
> 代码：仓库 `ScottChen0115/outlook-daily-digest`，分支 `cursor/web-demo-agent`，目录 `webdemo/`（[PR #1](https://github.com/ScottChen0115/outlook-daily-digest/pull/1)）。

## 1. 要提交的三样东西

| 提交项 | 文件 / 内容 | 状态 |
|---|---|---|
| 演示链接 | https://email-digest-agent-eo4s.onrender.com | ✅ 已上线，已验证 |
| 测试记录（约 300 词） | [`webdemo/docs/submission/test-log.md`](submission/test-log.md)（中文对照：[`test-log.zh.md`](submission/test-log.zh.md)） | 📝 待团队最终审核 |
| 示例场景（3–5 个） | [`webdemo/docs/submission/sample-scenarios.md`](submission/sample-scenarios.md) | 📝 待团队最终审核 |

另外，**每人**还要各自完成对 2 个其他组的同伴反馈。

## 2. 这是什么

原项目只能在 Mac 上读 Mail 应用里的邮件。网页版改成了**粘贴邮件**，部署在服务器上，评审打开链接就能用。

功能：
- 把一天的邮件按**四象限**分类：重要且紧急、重要不紧急、紧急不重要、都不是。
- 每封邮件生成一句话摘要，提取**待办和截止时间**。
- 重要待办置顶，可以一键忽略或恢复，刷新后状态保留。
- **聊天面板**：可以针对这批邮件提问，比如"今天要做什么""什么可以忽略"。只根据邮件内容回答，不编造。
- 内置 3 个示例收件箱：上班族、学生、边界情况（提示词注入、HTML 代码、中文、空标题、重复邮件）。

AI 调用：只用 **DeepSeek** 一个 API，模型 `deepseek-flash`。没有 key 时会使用离线 mock 模型，页面顶部有黄色横幅提示。线上版本固定使用真实模型，**不会**出现 mock。

## 3. 当前状态

| 项目 | 状态 |
|---|---|
| 网页版代码 | ✅ 完成 |
| 自动化测试 | ✅ 27/27 通过 |
| 标注集（24 封，用 `eval.py` 打分） | ✅ 象限 23/24，是否需要处理 24/24（真实 DeepSeek） |
| 三个示例场景检查 | ✅ 本地和线上都是 18/18 |
| 提示词注入（跑 3 次） | ✅ 3 次都没被骗 |
| 聊天完整性（2 个问题各 3 次） | ✅ 本地和线上都是 6/6 |
| Render 部署 | ✅ 已上线，使用真实模型 |

标注集的预期标签先由 AI 协助起草，再经团队审核后采用。

## 4. 测试中发现的问题

已修复：
- 问"有什么紧急的"，3 封紧急邮件只列出 1 封。改写提示词后完整。
- 聊天回答显示原始的 Markdown 星号，现在改为纯文字。
- 模型返回字符串 `"false"` 时，会生成假待办。
- 模型漏掉的邮件会被悄悄放进"可忽略"象限，现在标记为"需人工检查"。
- 重复邮件显示两次，现在会合并。
- 输入内容过大时连接直接断开（只在 Mac 上出现），现在正常提示"内容太大"。

选择不修复：
- Client B 周五截止的合同：多次运行时，有时判"重要且紧急"，有时判"重要不紧急"。两个都说得通。
- 生成新报告后，旧的聊天记录仍留在页面上，属于外观问题。
- 测试邮件是虚构的，数量也少，真实的长邮件串还没测过。

## 5. 本地运行

```bash
git checkout cursor/web-demo-agent
cd webdemo
cp .env.example .env                       # 填入 DEEPSEEK_API_KEY，并设 LLM_MODE=live
python3 server.py                          # 打开 http://localhost:8000
python3 -m unittest discover -s tests      # 自动化测试
python3 eval.py                            # 用标注集打分
```

只需要 Python 3.10 及以上，不用安装任何依赖。**API key 不在仓库里**，要用请找 Scott。

## 6. 部署说明

- 托管在 Render 免费版，从 `cursor/web-demo-agent` 分支自动部署。往这个分支推送代码，几分钟后线上会自动更新。
- key 只保存在 Render 后台的 **Environment** 页面里。key 出问题时，页面会提示"AI 服务配置有误"。
- 闲置 15 分钟后服务会休眠。**评审期间每天先打开一次链接。**
- 每次生成报告都会扣 DeepSeek 余额。目前余额充足，Scott 会定期查看。

## 7. 剩余待办

| # | 任务 | 负责人 | 截止 |
|---|---|---|---|
| 1 | 审核 `submission/test-log.md` 和 `submission/sample-scenarios.md`，包括末尾那句 AI 使用说明是否保留 | 全员 | 11/7 |
| 2 | 对照课程页面原文，确认截图里被涂掉的那段 AI 使用规定 | | 11/7 |
| 3 | 用自己的电脑和手机打开链接，把 5 个示例场景各试一遍 | 全员 | 11/7 |
| 4 | 在 FeedbackFruits 提交链接、测试记录和示例场景 | | 11/8 前 |
| 5 | 每人各自完成对 2 个其他组的同伴反馈 | 每人 | 11/8 23:59 |
| 6 | 评审期间每天打开一次链接，避免休眠 | | 评审期 |

## 8. 文件索引

| 文件 | 用途 |
|---|---|
| `webdemo/docs/submission/` | **要提交的测试记录和示例场景** |
| `webdemo/server.py` | 网页服务器和 API |
| `webdemo/digest.py` | 核心逻辑：解析邮件、分类、聊天 |
| `webdemo/llm.py` | DeepSeek 调用和 mock 切换 |
| `webdemo/mock_model.py` | 离线 mock 模型，仅用于没有 key 时的演示和测试 |
| `webdemo/static/` | 前端页面 |
| `webdemo/samples/sample_inboxes.json` | 3 个示例收件箱 |
| `webdemo/samples/eval_set.json` | 24 封标注邮件（团队审核后采用的标签） |
| `webdemo/tests/test_agent.py` | 自动化测试 |
| `webdemo/eval.py` | 准确率评估脚本 |
| `webdemo/docs/sample-scenarios.md` | 早期的场景草稿和手工测试计划（已被 `submission/` 取代） |
| `webdemo/docs/simulated-test-log.md` | 早期的 mock 模拟记录，**不可提交** |
| `render.yaml` | Render 部署配置 |
