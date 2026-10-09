# 🎯 BountyRadar - 开源悬赏雷达与自动化打金引擎

> **GitHub 目标账号**：[`dogecon6-wq`](https://github.com/dogecon6-wq)  
> **官方统一结算中心**：[https://psyverse.fun/payment](https://psyverse.fun/payment)  
> **EVM 统一收款钱包**：`0x240C74A953Fc04Fe8cD713c68b53e94d9b449F8C` (`gewenbo.eth`)  
> **PayPal 全球结算**：`https://paypal.me/gewenbo888`

---

## 💡 核心定位与赚钱逻辑

在开源社区（GitHub）赚钱，**绝对不是无脑堆砌 AI 垃圾 PR**（这会被项目方直接标记 `spam` 甚至封号），而是遵循极严谨的商业闭环：

1. **赏金工单猎人（Bounty Hunter）**：
   - **Algora (algora.io)**：全球最大开源 Issue 悬赏平台，PR 合并后直接结算美元 / Crypto。
   - **Polar.sh & Opire**：开源 Issue 赞助与赏金池。
   - **BasedHardware/omi 等活跃 AI 开源硬件生态**：每个安全漏洞/边界加固/功能修复 PR 悬赏 **\$50 ~ \$100 USDC**，直接链上秒结。
   - **OnlyDust (onlydust.com)**：Web3 基金会官方开源打金平台，代码合并直接领 USDC。

2. **手术刀式代码修复（Surgical Bug Fix）**：
   - 寻找真实存在的系统缺陷（信息泄露、未捕获异常、显式空值数据库投毒、EXIF 敏感元数据泄露等）。
   - 只改 5~15 行核心代码，不碰任何无关结构。
   - 附带 3 组行为级单元测试（测试 1 必挂、测试 2 验证修复、测试 3 确保向后兼容）。

---

## 🚀 快速上手与使用指南

### 1. 全网实时扫描带金工单

运行雷达引擎，自动抓取全网最新悬赏工单（按竞争热度与赏金加权排序）：

```bash
python3 bounty_radar.py --limit 15
```

### 2. 深度分析指定工单并生成打金方案

看中某个工单后，一键生成针对该工单的克隆命令、隔离分支、提交身份与 PR 模板：

```bash
python3 bounty_radar.py --analyze https://github.com/BasedHardware/omi/issues/20461
```

### 3. 作为 MCP Server 接入 AI 编辑器（Cursor / Claude Desktop / Antigravity）

本项目原生支持 **Model Context Protocol (MCP)**。将以下配置加入到你的 `claude_desktop_config.json` 或 Cursor MCP 配置中：

```json
{
  "mcpServers": {
    "bounty-radar": {
      "command": "python3",
      "args": ["/Users/geir/Downloads/gewenbo/dogecon6/mcp_server.py"]
    }
  }
}
```

接入后，你可直接在对话框中要求 AI：
- *"扫描当前最少人竞争的开源美金工单"*
- *"分析此 GitHub Issue 并生成手术刀修复方案"*

---

## 🛠️ 本地身份与 Git 隔离配置

为了确保所有的提交记录和 PR 都精准计入 `dogecon6-wq` 账号，请在当前仓库确认配置：

```bash
# 1. 设置本地 Git 提交身份（仅限当前仓库）
git config user.name "dogecon6-wq"
git config user.email "339028173+dogecon6-wq@users.noreply.github.com"

# 2. 验证配置
git config user.name
git config user.email
```

---

## 📋 目录架构

```text
dogecon6/
├── bounty_radar.py            # 全网悬赏扫描与打金辅助 CLI 引擎
├── mcp_server.py              # Model Context Protocol (MCP) 标准服务接口
├── safe_hunter.py             # 六重防封号门禁自检与合规 PR 生成器
├── run_bounty_fix.py          # 首单 $50 修复补丁、单测与 PR/Bounty 提案全套脚本
├── README.md                  # 本项目使用说明与打金指南
├── PROFILE_README.md          # 专为 dogecon6-wq 定制的高端 GitHub Profile 主页模板
└── docs/
    └── PR_MERGE_PLAYBOOK.md   # 手术刀式 PR 与 100% 合并防封 SOP
```
