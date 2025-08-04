## Software Design Report: LangGraph Chatbot

### 1. Project Scope

- Simple rule-based chatbot
- Core functionality: Answer FAQs, route to human agent
- Tech stack: LangGraph for workflow orchestration

### 2. Architecture

```mermaid
graph TD
    A[User Input] --> B{NLU Engine}
    B -->|Intent Detected| C[LangGraph Router]
    C --> D[FAQ Knowledge Base]
    C --> E[Human Agent Handoff]
    D --> F[Response Generation]
    E --> G[Live Chat Interface]
```
