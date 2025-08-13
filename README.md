# project-planning-genie

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Linter: Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

An intelligent AI-powered project planning agent that transforms project descriptions into comprehensive, actionable implementation plans. Built with LangGraph and multi-agent architecture to deliver structured markdown reports perfect for GitHub issues and project management.

## 🚀 Overview

This project planning agent helps developers and teams break down complex project ideas into manageable, step-by-step implementation plans. By leveraging advanced AI agents and workflow orchestration, it generates detailed project roadmap that can be directly used as GitHub issues, project boards, or documentation.

![Architecture Diagram](assets/final_graph.png)

**Key Features:**

- **Intelligent Project Analysis**: Automatically decomposes project descriptions into actionable tasks
- **Multi-Agent Architecture**: Specialized agents for clarification, planning (supervisor and researcher), and report generation
- **Markdown Report Generation**: Outputs formatted plans ready for GitHub issues
- **Extensible Design**: Built with modern software engineering patterns for easy enhancement

## 🎯 What It Does

1. **Project Intake**: Accepts natural language project descriptions
2. **Requirement Clarification**: Asks intelligent questions to resolve ambiguities
3. **Task Decomposition**: Breaks down projects into logical phases and tasks
4. **Plan Generation**: Creates structured markdown reports with checkboxes and priorities
5. **Validation**: Reviews and refines plans for completeness and feasibility

## 🏗️ Architecture

The project is built on a multi-agent architecture orchestrated by LangGraph. Each agent has a specialized role, ensuring a clear separation of concerns and making the system modular and extensible.

## ✨ Example Outputs

You can find more generated project plans in the [`generated_examples/`](./generated_examples/) directory. Here is a direct link to one of them:

- **Agent-Powered AI Note-Taking App**: A comprehensive plan for building an AI note-taking application with a focus on clean architecture and modern engineering practices.

### Agent Workflow

1. **Clarification Agent**: The first point of contact. It analyzes the user's initial request to determine if it's clear enough for planning. If not, it generates clarifying questions to resolve ambiguities before proceeding.
2. **Supervisor Agent**: Acts as the project manager. It receives the clarified request, breaks it down into smaller research topics, and dispatches tasks to the Research Agents. It reviews the research findings to decide if more information is needed or if planning can commence.
3. **Research Agent**: Executes deep research on specific topics assigned by the Supervisor. It uses tools like Tavily to search the web for best practices, technology stacks, and architectural patterns.
4. **Report Generation Agent**: The final step. It synthesizes all the research findings into a comprehensive, well-structured markdown document, following the format defined in the `system_prompt_project_plan_structure.md`.

## 🛠️ Technology Stack

| Category          | Technology / Library | Justification                                                                    |
| ----------------- | -------------------- | -------------------------------------------------------------------------------- |
| **Orchestration** | LangGraph            | Provides a powerful way to build stateful, multi-agent applications with cycles. |
| **Language**      | Python 3.13+         | Modern Python features and strong support for AI/ML libraries.                   |
| **AI Models**     | OpenAI, Perplexity   | Access to powerful Large Language Models for generation and reasoning.           |
| **Web Research**  | Tavily               | Specialized search API for AI agents, providing concise and relevant results.    |
| **Logging**       | Loguru               | Simple and powerful logging for better debugging and monitoring.                 |
| **Testing**       | pytest               | Standard for testing in the Python ecosystem, enabling robust test suites.       |
| **Environment**   | uv, python-dotenv    | Fast, modern package management and easy handling of environment variables.      |

## 🎨 Project Structure

```
project-planning-genie/
├── src/
│   └── agent/
│       ├── prompts/              # System prompts for agents
│       │   ├── __init__.py
│       │   └── *.md
│       ├── __init__.py
│       ├── configuration.py      # Configuration management
│       ├── researcher_agent.py   # Research agent logic
│       ├── supervisor_agent.py   # Supervisor agent logic
│       └── ...                   # Other agent and core files
├── assets/
│   └── final_graph.png           # Architecture diagram
├── docs/
│   └── *.md
├── tests/
│   └── ...
├── .env.example                  # Example environment file
├── README.md
└── uv.lock
```

## 🚦 Getting Started

### Prerequisites

- Python 3.13+
- `uv` package manager (installation instructions)

### Quick Start

1. **Clone the repository:**

   ```bash
   https://github.com/vivekpatel99/project-planning-genie.git
   cd project-planning-genie
   ```

2. **Create and Activate Virtual Environment (using `uv`)/Setup Project Environment:**

   ```bash
   # This command creates a virtual environment in .venv if it doesn't exist,
   # and installs the dependencies specified in pyproject.toml
   uv sync
   ```

3. **Set up Environment Variables:**

   - **`.env` file (Recommended for Local Development)**

     - Create a `.env` file in the project root by copying the example: `cp .env.example .env`
     - Add your credentials and configurations:

     ```dotenv
        # .env
        TAVILY_API_KEY=your_tavily_api_key
        LANGCHAIN_API_KEY=
        OPENAI_API_KEY=

        LANGSMITH_PROJECT=
        LANGCHAIN_TRACING_V2=true
     ```

     - To have VS Code automatically load the `.env` file, add the following line to your `.vscode/settings.json`:

     ```json
     "python.envFile": "${workspaceFolder}/.env"
     ```

### Usage

```bash
# Run the main application (update with your actual entry point)
langgraph dev # select project_planning_genie graph
```

## 🔮 Future Enhancements

- **GitHub Integration**: Automatically create issues and pull requests from generated plans (If human approves)
- **User Feedback Loop**: Incorporate user feedback to improve task generation
- **Performance Analytics**: Track token usage, response times, and accuracy metrics

## 📚 Reference

1. [open_deep_research](https://github.com/langchain-ai/open_deep_research/tree/main)
2. [Open Deep Research-Youtube](https://www.youtube.com/watch?v=agGiWUpxkhg)
3. [LangGraph](https://github.com/langchain-ai/langgraph)
4. https://github.com/kenneth-liao/human-in-the-loop/tree/main
5. [KennyLio-MCP Tutorial](https://www.youtube.com/watch?v=Uft4VwGm5qs&t=1410s)
6. [File System MCP Server](https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem#docker)
7. https://github.com/esxr/langgraph-mcp/tree/main
