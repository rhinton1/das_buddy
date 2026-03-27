#!/usr/bin/env python3
"""
MCP Server for Jira integration
Provides tools to interact with Jira issues, projects, and workflows
"""

import os
import json
import asyncio
from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
import mcp.server.stdio
from jira import JIRA
from jira.exceptions import JIRAError

# Initialize MCP server
mcpSvr = Server("JiraServer")

# Global Jira client
jira_client = None

def get_jira_client() -> JIRA:
    """Initialize and return Jira client"""
    global jira_client

    if jira_client is None:
        jira_url = os.getenv("JIRA_URL")
        jira_email = os.getenv("JIRA_EMAIL")
        jira_api_token = os.getenv("JIRA_API_TOKEN")

        if not all([jira_url, jira_email, jira_api_token]):
            raise ValueError(
                "Missing required environment variables: JIRA_URL, JIRA_EMAIL, JIRA_API_TOKEN"
            )

        jira_client = JIRA(
            server=jira_url,
            basic_auth=(jira_email, jira_api_token)
        )

    return jira_client

@mcpSvr.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available Jira tools"""
    return [
        types.Tool(
            name="search-issues",
            description="Search for Jira issues using JQL (Jira Query Language)",
            inputSchema={
                "type": "object",
                "properties": {
                    "jql": {
                        "type": "string",
                        "description": "JQL query string (e.g., 'project = PROJ AND status = Open')"
                    },
                    "max_results": {
                        "type": "number",
                        "description": "Maximum number of results to return (default: 50)",
                        "default": 50
                    }
                },
                "required": ["jql"]
            }
        ),
        types.Tool(
            name="get-issue",
            description="Get detailed information about a specific Jira issue",
            inputSchema={
                "type": "object",
                "properties": {
                    "issue_key": {
                        "type": "string",
                        "description": "Jira issue key (e.g., 'PROJ-123')"
                    }
                },
                "required": ["issue_key"]
            }
        ),
        types.Tool(
            name="create-issue",
            description="Create a new Jira issue",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_key": {
                        "type": "string",
                        "description": "Project key (e.g., 'PROJ')"
                    },
                    "summary": {
                        "type": "string",
                        "description": "Issue summary/title"
                    },
                    "description": {
                        "type": "string",
                        "description": "Issue description"
                    },
                    "issue_type": {
                        "type": "string",
                        "description": "Issue type (e.g., 'Task', 'Bug', 'Story')",
                        "default": "Task"
                    },
                    "priority": {
                        "type": "string",
                        "description": "Priority (e.g., 'High', 'Medium', 'Low')"
                    },
                    "assignee": {
                        "type": "string",
                        "description": "Assignee username or email"
                    },
                    "labels": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of labels"
                    }
                },
                "required": ["project_key", "summary", "issue_type"]
            }
        ),
        types.Tool(
            name="update-issue",
            description="Update an existing Jira issue",
            inputSchema={
                "type": "object",
                "properties": {
                    "issue_key": {
                        "type": "string",
                        "description": "Jira issue key (e.g., 'PROJ-123')"
                    },
                    "summary": {
                        "type": "string",
                        "description": "New summary/title"
                    },
                    "description": {
                        "type": "string",
                        "description": "New description"
                    },
                    "assignee": {
                        "type": "string",
                        "description": "New assignee username or email"
                    },
                    "priority": {
                        "type": "string",
                        "description": "New priority"
                    },
                    "labels": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "New list of labels"
                    }
                },
                "required": ["issue_key"]
            }
        ),
        types.Tool(
            name="add-comment",
            description="Add a comment to a Jira issue",
            inputSchema={
                "type": "object",
                "properties": {
                    "issue_key": {
                        "type": "string",
                        "description": "Jira issue key (e.g., 'PROJ-123')"
                    },
                    "comment": {
                        "type": "string",
                        "description": "Comment text"
                    }
                },
                "required": ["issue_key", "comment"]
            }
        ),
        types.Tool(
            name="transition-issue",
            description="Transition a Jira issue to a new status",
            inputSchema={
                "type": "object",
                "properties": {
                    "issue_key": {
                        "type": "string",
                        "description": "Jira issue key (e.g., 'PROJ-123')"
                    },
                    "transition": {
                        "type": "string",
                        "description": "Transition name (e.g., 'Done', 'In Progress', 'To Do')"
                    }
                },
                "required": ["issue_key", "transition"]
            }
        ),
        types.Tool(
            name="list-projects",
            description="List all accessible Jira projects",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        types.Tool(
            name="get-project",
            description="Get detailed information about a specific project",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_key": {
                        "type": "string",
                        "description": "Project key (e.g., 'PROJ')"
                    }
                },
                "required": ["project_key"]
            }
        )
    ]

@mcpSvr.call_tool()
async def handle_call_tool(
        name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle tool execution requests"""

    try:
        jira_client = get_jira_client()

        if name == "search-issues":
            jql = arguments.get("jql")
            max_results = arguments.get("max_results", 50)

            issues = jira_client.search_issues(jql, maxResults=max_results)

            results = []
            for issue in issues:
                results.append({
                    "key": issue.key,
                    "summary": issue.fields.summary,
                    "status": issue.fields.status.name,
                    "assignee": issue.fields.assignee.displayName if issue.fields.assignee else "Unassigned",
                    "priority": issue.fields.priority.name if issue.fields.priority else "None",
                    "created": issue.fields.created,
                    "updated": issue.fields.updated
                })

            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(results, indent=2)
                )
            ]

        elif name == "get-issue":
            issue_key = arguments.get("issue_key")
            issue = jira_client.issue(issue_key)

            issue_data = {
                "key": issue.key,
                "summary": issue.fields.summary,
                "description": issue.fields.description or "",
                "status": issue.fields.status.name,
                "assignee": issue.fields.assignee.displayName if issue.fields.assignee else "Unassigned",
                "reporter": issue.fields.reporter.displayName if issue.fields.reporter else "Unknown",
                "priority": issue.fields.priority.name if issue.fields.priority else "None",
                "issue_type": issue.fields.issuetype.name,
                "created": issue.fields.created,
                "updated": issue.fields.updated,
                "labels": issue.fields.labels,
                "comments": [
                    {
                        "author": comment.author.displayName,
                        "body": comment.body,
                        "created": comment.created
                    }
                    for comment in issue.fields.comment.comments
                ]
            }

            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(issue_data, indent=2)
                )
            ]

        elif name == "create-issue":
            project_key = arguments.get("project_key")
            summary = arguments.get("summary")
            description = arguments.get("description", "")
            issue_type = arguments.get("issue_type", "Task")
            priority = arguments.get("priority")
            assignee = arguments.get("assignee")
            labels = arguments.get("labels", [])

            issue_dict = {
                'project': {'key': project_key},
                'summary': summary,
                'description': description,
                'issuetype': {'name': issue_type},
            }

            if priority:
                issue_dict['priority'] = {'name': priority}

            if assignee:
                issue_dict['assignee'] = {'name': assignee}

            if labels:
                issue_dict['labels'] = labels

            new_issue = jira_client.create_issue(fields=issue_dict)

            return [
                types.TextContent(
                    type="text",
                    text=f"Issue created successfully: {new_issue.key}\nURL: {jira_client.server_url}/browse/{new_issue.key}"
                )
            ]

        elif name == "update-issue":
            issue_key = arguments.get("issue_key")
            issue = jira_client.issue(issue_key)

            update_fields = {}

            if "summary" in arguments:
                update_fields['summary'] = arguments['summary']

            if "description" in arguments:
                update_fields['description'] = arguments['description']

            if "priority" in arguments:
                update_fields['priority'] = {'name': arguments['priority']}

            if "assignee" in arguments:
                update_fields['assignee'] = {'name': arguments['assignee']}

            if "labels" in arguments:
                update_fields['labels'] = arguments['labels']

            issue.update(fields=update_fields)

            return [
                types.TextContent(
                    type="text",
                    text=f"Issue {issue_key} updated successfully"
                )
            ]

        elif name == "add-comment":
            issue_key = arguments.get("issue_key")
            comment_text = arguments.get("comment")

            jira_client.add_comment(issue_key, comment_text)

            return [
                types.TextContent(
                    type="text",
                    text=f"Comment added to {issue_key} successfully"
                )
            ]

        elif name == "transition-issue":
            issue_key = arguments.get("issue_key")
            transition_name = arguments.get("transition")

            # Get available transitions
            transitions = jira_client.transitions(issue_key)
            transition_id = None

            for t in transitions:
                if t['name'].lower() == transition_name.lower():
                    transition_id = t['id']
                    break

            if transition_id is None:
                available = [t['name'] for t in transitions]
                return [
                    types.TextContent(
                        type="text",
                        text=f"Transition '{transition_name}' not found. Available transitions: {', '.join(available)}"
                    )
                ]

            jira_client.transition_issue(issue_key, transition_id)

            return [
                types.TextContent(
                    type="text",
                    text=f"Issue {issue_key} transitioned to '{transition_name}' successfully"
                )
            ]

        elif name == "list-projects":
            projects = jira_client.projects()

            project_list = [
                {
                    "key": project.key,
                    "name": project.name,
                    "lead": project.lead.displayName if hasattr(project, 'lead') else "Unknown"
                }
                for project in projects
            ]

            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(project_list, indent=2)
                )
            ]

        elif name == "get-project":
            project_key = arguments.get("project_key")
            project = jira_client.project(project_key)

            project_data = {
                "key": project.key,
                "name": project.name,
                "description": project.description if hasattr(project, 'description') else "",
                "lead": project.lead.displayName if hasattr(project, 'lead') else "Unknown",
                "url": f"{jira_client.server_url}/browse/{project.key}"
            }

            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(project_data, indent=2)
                )
            ]

        else:
            raise ValueError(f"Unknown tool: {name}")

    except JIRAError as e:
        return [
            types.TextContent(
                type="text",
                text=f"Jira API Error: {e.status_code} - {e.text}"
            )
        ]
    except Exception as e:
        return [
            types.TextContent(
                type="text",
                text=f"Error: {str(e)}"
            )
        ]

async def main():
    """Run the MCP server"""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await mcpSvr.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="jira-mcp-server",
                server_version="0.1.0",
                capabilities=mcpSvr.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())
