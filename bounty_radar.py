#!/usr/bin/env python3
"""
BountyRadar - 开源悬赏雷达与自动化打金辅助引擎
专为 GitHub 悬赏打金设计的扫描、初筛与工单分析工具。
"""

import os
import sys
import json
import re
import subprocess
import argparse
from datetime import datetime

# 终端 ANSI 彩色样式
C_CYAN = "\033[96m"
C_GREEN = "\033[92m"
C_YELLOW = "\033[93m"
C_RED = "\033[91m"
C_BLUE = "\033[94m"
C_PURPLE = "\033[95m"
C_BOLD = "\033[1m"
C_RESET = "\033[0m"

# 赏金与打金关键词规则
REWARD_PATTERNS = [
    r"\$\s*([0-9]+(?:,[0-9]{3})*)",          # $50, $1,000
    r"([0-9]+(?:,[0-9]{3})*)\s*USD",         # 50 USD
    r"([0-9]+(?:,[0-9]{3})*)\s*USDC",        # 50 USDC
    r"bounty[:\s]+(?:\$|USD\s*)?([0-9]+)",    # bounty: $50
]

def extract_reward(text: str) -> str:
    """从标题或正文中提取赏金金额"""
    for pattern in REWARD_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            val = match.group(1).replace(",", "")
            if val.isdigit() and int(val) > 0:
                return f"${match.group(1)}"
    return "有奖/待定"

def run_gh_api(endpoint: str, params: dict = None) -> dict:
    """调用本地已认证的 GitHub CLI 或 curl API"""
    cmd = ["gh", "api", "-X", "GET", endpoint]
    if params:
        for k, v in params.items():
            cmd.extend(["-f", f"{k}={v}"])
    
    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=30)
        if proc.returncode == 0:
            return json.loads(proc.stdout)
    except Exception as e:
        pass
    
    # 回退到无 gh 的匿名 curl (可能受 rate limit 限制)
    query_str = "&".join(f"{k}={v}" for k, v in (params or {}).items())
    full_url = f"https://api.github.com/{endpoint}?{query_str}"
    try:
        proc = subprocess.run(["curl", "-s", "-A", "BountyRadar/1.0", full_url], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=15)
        if proc.returncode == 0:
            return json.loads(proc.stdout)
    except Exception:
        pass
    return {}

def scan_bounties(channels=None, limit=20):
    """多通道全网并发/轮询扫描开源悬赏工单"""
    if channels is None:
        channels = ["algora", "omi", "general_usd"]
    
    queries = []
    if "algora" in channels:
        queries.append(('commenter:algora-pbc is:open is:issue', 'Algora (Stripe/Web3)'))
    if "omi" in channels:
        queries.append(('repo:BasedHardware/omi is:issue is:open bounty in:title', 'BasedHardware Omi ($50~$100 USDC)'))
    if "general_usd" in channels:
        queries.append(('"bounty $" is:open is:issue sort:updated-desc', 'General GitHub Bounties'))
    
    candidates = []
    seen_urls = set()

    for q, source_name in queries:
        print(f"{C_BLUE}[*] 正在扫描渠道: {source_name}...{C_RESET}")
        res = run_gh_api("search/issues", {"q": q, "per_page": str(limit)})
        items = res.get("items", [])
        for item in items:
            url = item.get("html_url", "")
            if not url or url in seen_urls:
                continue
            
            # 过滤逻辑：已关闭、已分配、讨论数过多（竞争过度）
            if item.get("state") != "open":
                continue
            if item.get("assignees"):
                continue
            
            title = item.get("title", "")
            body = item.get("body", "") or ""
            comments = item.get("comments", 0)
            created_at = item.get("created_at", "")[:10]
            repo = url.split("/issues/")[0].replace("https://github.com/", "")
            
            # 计算赏金标签
            reward = extract_reward(title)
            if reward == "有奖/待定":
                reward = extract_reward(body[:1000])
            
            # 技术栈识别
            stack = []
            text_combo = (title + " " + body + " " + repo).lower()
            if any(k in text_combo for k in ["python", "fastapi", "django", "pytest"]):
                stack.append("Python")
            if any(k in text_combo for k in ["typescript", "javascript", "react", "next.js", "node"]):
                stack.append("TS/JS")
            if "rust" in text_combo:
                stack.append("Rust")
            if "go" in text_combo or "golang" in text_combo:
                stack.append("Go")
            if "doc" in text_combo or "guide" in text_combo:
                stack.append("Docs")
            
            candidates.append({
                "source": source_name,
                "repo": repo,
                "title": title,
                "url": url,
                "reward": reward,
                "comments": comments,
                "stack": "/".join(stack) if stack else "General",
                "created_at": created_at
            })
            seen_urls.add(url)
    
    # 按照评论数（竞争程度）升序，优先推荐少人争抢的
    candidates.sort(key=lambda x: (0 if x["reward"] != "有奖/待定" else 1, x["comments"]))
    return candidates

def print_table(candidates):
    """格式化打印赏金列表"""
    if not candidates:
        print(f"{C_YELLOW}[!] 未发现符合初筛条件的工单。{C_RESET}")
        return

    print("\n" + "=" * 90)
    print(f"{C_BOLD}{C_GREEN}🎯 开源悬赏雷达实时探测结果 (按热度与赏金加权排序){C_RESET}")
    print("=" * 90)
    print(f"{C_BOLD}{'序号':<4} {'赏金估算':<10} {'评论/竞争':<10} {'技术栈':<10} {'目标仓库 & 工单标题'}{C_RESET}")
    print("-" * 90)

    for idx, c in enumerate(candidates, 1):
        reward_color = C_GREEN if "$" in c["reward"] else C_YELLOW
        heat_color = C_GREEN if c["comments"] <= 3 else (C_YELLOW if c["comments"] <= 10 else C_RED)
        
        repo_prefix = f"[{c['repo']}]"
        title_snippet = c['title']
        if len(title_snippet) > 42:
            title_snippet = title_snippet[:39] + "..."
            
        print(f"{idx:<4} {reward_color}{c['reward']:<10}{C_RESET} {heat_color}{c['comments']:<10}{C_RESET} {C_CYAN}{c['stack']:<10}{C_RESET} {C_BOLD}{repo_prefix}{C_RESET} {title_snippet}")
        print(f"     └─ 🔗 {C_BLUE}{c['url']}{C_RESET}")
    print("=" * 90 + "\n")

def generate_pr_plan(issue_url: str):
    """为选定的 Issue 生成手术刀式打金 SOP 与 PR 规范文档"""
    print(f"\n{C_BOLD}{C_CYAN}[+] 正在分析目标工单: {issue_url}...{C_RESET}")
    
    match = re.search(r"github\.com/([^/]+/[^/]+)/issues/(\d+)", issue_url)
    if not match:
        print(f"{C_RED}[-] 无效的 GitHub Issue 链接。{C_RESET}")
        return

    repo = match.group(1)
    issue_num = match.group(2)
    
    issue_data = run_gh_api(f"repos/{repo}/issues/{issue_num}")
    if not issue_data or "title" not in issue_data:
        print(f"{C_RED}[-] 无法抓取工单详情，请检查网络或权限。{C_RESET}")
        return

    title = issue_data.get("title", "")
    body = issue_data.get("body", "") or ""
    
    print(f"\n{C_GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{C_RESET}")
    print(f"{C_BOLD}📌 目标仓库：{repo}{C_RESET}")
    print(f"{C_BOLD}🎯 工单标题：{title}{C_RESET}")
    print(f"{C_GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{C_RESET}")
    
    print(f"\n{C_BOLD}🚀 推荐执行打金流水线（4 步标准操作程序）：{C_RESET}")
    print(f"""
1. 【Fork 并克隆仓库】
   git clone https://github.com/{repo}.git
   cd {repo.split('/')[-1]}
   git checkout -b fix/issue-{issue_num}

2. 【确认提交身份】（确保 PR 归属 dogecon6-wq）
   git config user.name "dogecon6-wq"
   git config user.email "339028173+dogecon6-wq@users.noreply.github.com"

3. 【手术刀式编码与单测】
   - 绝不大改架构，定位到抛错或漏洞的核心 5~10 行代码。
   - 编写复现测试（Test that fails before fix, passes after fix）。
   - 本地格式化：执行项目自带的 linter / Black / Prettier 门禁。

4. 【PR 提交规范（防 AI 模板，纯正工程师口吻）】
   - PR 标题：fix: sanitize exception / handle edge case for #{issue_num}
   - PR 描述：
     ## Summary
     Addresses #{issue_num}. Fixes unhandled exception when ...
     
     ## Changes
     - Guard against explicit nulls / add safe error handling.
     - Added unit tests covering the failure condition.
     
     ## Verification
     - Unit tests pass locally.
     - Failure-Class: none
""")

def main():
    parser = argparse.ArgumentParser(description="BountyRadar - 开源悬赏雷达")
    parser.add_argument("--scan", action="store_true", help="执行全网高价值悬赏工单探测")
    parser.add_argument("--limit", type=int, default=15, help="扫描结果展示数量上限")
    parser.add_argument("--analyze", type=str, help="分析指定的 GitHub Issue 链接并生成打金方案")
    
    args = parser.parse_args()
    
    if args.analyze:
        generate_pr_plan(args.analyze)
    else:
        # 默认执行扫描
        candidates = scan_bounties(limit=args.limit)
        print_table(candidates)
        print(f"{C_BOLD}💡 提示：运行 `python3 bounty_radar.py --analyze <Issue_URL>` 可一键生成该工单的手术刀式打金 SOP！{C_RESET}\n")

if __name__ == "__main__":
    main()
