#!/usr/bin/env python3
"""
BountyRadar MCP Server
Model Context Protocol (MCP) server enabling AI assistants (Claude, Cursor, Windsurf)
to query real-time GitHub open-source bounties and generate surgical fix blueprints.
"""

import sys
import json
import logging
from typing import Any, Dict, List

# Import core scanner functions
from bounty_radar import scan_bounties, extract_reward, run_gh_api

logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger("bounty-radar-mcp")

TOOLS = [
    {
        "name": "scan_bounties",
        "description": "Scan GitHub for active paid open-source bounties across Algora, BasedHardware, and Web3 ecosystems.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of bounty opportunities to retrieve (default: 10)",
                    "default": 10
                },
                "channels": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Channels to scan: 'algora', 'omi', 'general_usd' (default: all)",
                    "default": ["algora", "omi", "general_usd"]
                }
            }
        }
    },
    {
        "name": "analyze_bounty",
        "description": "Analyze a specific GitHub bounty issue URL and generate a surgical defect resolution blueprint with anti-ban guidelines.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "issue_url": {
                    "type": "string",
                    "description": "Full URL of the GitHub Issue (e.g., https://github.com/BasedHardware/omi/issues/20897)"
                }
            },
            "required": ["issue_url"]
        }
    }
]

def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
    if name == "scan_bounties":
        limit = arguments.get("limit", 10)
        channels = arguments.get("channels", ["algora", "omi", "general_usd"])
        candidates = scan_bounties(channels=channels, limit=limit)
        
        # Format results as readable markdown text
        lines = ["# 🎯 Active Open-Source Bounty Scan Results\n"]
        for idx, c in enumerate(candidates, 1):
            lines.append(f"### {idx}. {c['title']}")
            lines.append(f"- **Reward:** `{c['reward']}`")
            lines.append(f"- **Repository:** `{c['repo']}`")
            lines.append(f"- **Tech Stack:** `{c['stack']}`")
            lines.append(f"- **Comments / Heat:** {c['comments']}")
            lines.append(f"- **URL:** {c['url']}\n")
            
        return [{"type": "text", "text": "\n".join(lines)}]

    elif name == "analyze_bounty":
        issue_url = arguments.get("issue_url", "")
        import re
        match = re.search(r"github\.com/([^/]+/[^/]+)/issues/(\d+)", issue_url)
        if not match:
            return [{"type": "text", "text": "Error: Invalid GitHub issue URL."}]
        
        repo, issue_num = match.group(1), match.group(2)
        issue_data = run_gh_api(f"repos/{repo}/issues/{issue_num}")
        if not issue_data:
            return [{"type": "text", "text": f"Error: Could not retrieve issue details for {repo}#{issue_num}."}]
        
        title = issue_data.get("title", "")
        body = issue_data.get("body", "") or ""
        comments = issue_data.get("comments", 0)
        
        text = f"""# 🔍 Bounty Defect Analysis: {repo}#{issue_num}
- **Title:** {title}
- **Competition (Comments):** {comments}
- **Status:** {issue_data.get('state')}

## 🚀 Recommended Surgical Plan
1. **Scope Limit**: Keep changes under 20 lines to prevent AI spam flags.
2. **Hermetic Testing**: Add 2 unit tests (one failing without patch, one passing with patch).
3. **Format Contract**: Follow the target repository's linter and Failure-Class declarations.
"""
        return [{"type": "text", "text": text}]
    
    return [{"type": "text", "text": f"Unknown tool: {name}"}]

def run_server():
    """Standard JSON-RPC Stdio Loop for Model Context Protocol"""
    logger.info("BountyRadar MCP server started on stdio")
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
            line = line.strip()
            if not line:
                continue
            
            request = json.loads(line)
            method = request.get("method")
            msg_id = request.get("id")

            if method == "initialize":
                response = {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "serverInfo": {"name": "bounty-radar-mcp", "version": "0.2.0"},
                        "capabilities": {"tools": {}}
                    }
                }
            elif method == "tools/list":
                response = {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {"tools": TOOLS}
                }
            elif method == "tools/call":
                params = request.get("params", {})
                tool_name = params.get("name")
                tool_args = params.get("arguments", {})
                content = handle_call_tool(tool_name, tool_args)
                response = {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {"content": content}
                }
            else:
                response = {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {"code": -32601, "message": f"Method {method} not found"}
                }
            
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()
        except Exception as e:
            logger.error(f"Error handling MCP request: {e}")

if __name__ == "__main__":
    run_server()
