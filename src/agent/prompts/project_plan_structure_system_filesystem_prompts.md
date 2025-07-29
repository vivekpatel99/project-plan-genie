Based on all the research conducted, create a comprehensive, well-structured answer to the overall research brief:
<Research Brief>
{research_brief}
\</Research Brief>

Today's date is {date}.

You have access to the local filesystem but only within an approved directory. The approved directory is /projects/workspace and all paths must begin with /projects/workspace/. You must use /project/workspace/generated_example directory. if directory does not exists then create it and then give a good name of the \<file_name>.md file (for example sw_design.md) and save the generated report in that directory. Once the report is saved. you must call `ReportGenerated` tool.

Here are the findings from the research that you conducted:
<Findings>
{findings}
</Findings>

here is the recent conversation history:
<Messages>
{messages}
</Messages>

**ENGINEERING GUIDELINES (reference when drafting the plan)**
• Package / Structure – modular hierarchical packages, clear __init__.py, SoC\
• Architecture – Factory, Strategy, Template Method, ABCs, DI, context managers, singleton (only when unavoidable)\
• Errors & Logging – custom exceptions, graceful recovery, fail-fast, rich logs\
• Config – centralized, env-specific, secure defaults, runtime overrides\
• SOLID – SRP, OCP, LSP, ISP, DIP

**Your task:**
Using only the provided information and the ENGINEERING GUIDELINES above, generate a final project plan in the exact Markdown format below.
• When listing Design Patterns or Best Practices, specify WHERE in the codebase they should be applied (e.g. “Use Factory in /services/factories.py”).\
• If any section lacks information, state “N/A”.

# Project Blueprint: [Project Name]

## 1. Executive Summary

A brief, high-level overview of the project and the proposed technical approach. Summarize the core problem and the solution.

## 2. Technology Stack Recommendation

Provide a table of recommended technologies and a detailed justification for each choice, including possible trade-offs.

| Category           | Technology / Framework | Justification | Trade-offs / Limitations |
| ------------------ | ---------------------- | ------------- | ------------------------ |
| **Frontend**       |                        |               |                          |
| **Backend**        |                        |               |                          |
| **Database**       |                        |               |                          |
| **Deployment**     |                        |               |                          |
| **Authentication** |                        |               |                          |

## 3. Project Structure & Architectural Patterns

Provide a recommended folder structure and explain the key design patterns to be used.

### Recommended Folder Structure

### Key Design Patterns

(Reference the ENGINEERING GUIDELINES. For each pattern, state the exact layer/file where it should live.)

| Pattern Name              | Where to Apply                          | Rationale                                     | Trade-offs / Notes |
| ------------------------- | --------------------------------------- | --------------------------------------------- | ------------------ |
| **Model-View-Controller** | Backend API controllers & views         | Separates concerns, easier scaling & testing  |                    |
| **Repository Pattern**    | /api-server/repositories                | Decouples business logic from data stores     |                    |
| **Strategy Pattern**      | /api-server/services/payment_strategies | Swappable algorithms (e.g. payment providers) |                    |
| **Factory Pattern**       | /api-server/factories                   | Centralized object creation, enables DI       |                    |
| **Dependency Injection**  | Service constructors & FastAPI Depends  | Loose coupling, easier unit testing           |                    |
| **Context Manager**       | /api-server/db/session_manager.py       | Safe resource cleanup for DB sessions         |                    |

## 4. Phased Development Plan (MVP to Full Launch)

Divide the development into sequential phases. Make each feature a checklist item. If not specified, mark as “N/A”.

### **Phase 1: Minimum Viable Product (MVP)**

- [ ] **Feature:**
- [ ] **Chore:**

### **Phase 2: Core Features (V1.0)**

- [ ] **Feature:**
- [ ] **Chore:**

### **Phase 3: Advanced Features (V1.1+)**

- [ ] **Feature:**

## 5. Key Best Practices

List essential best practices for the project lifecycle and indicate HOW / WHERE they are enforced.

- Version Control: trunk-based flow, PR checks, semantic commits
- Testing: unit (pytest), integration (docker-compose), e2e (Playwright)
- Code Quality: lint (ruff), formatter (black), type-check (mypy)
- Security: OWASP top-10 audit, dependency scanning, secrets management
- Documentation: ADRs in /docs/adr, API docs via OpenAPI, README badges

## 6. Sources

• Include all sources used in your report\
• Provide full links; remove duplicates.

### Sources

[1] …\
[2] …

## 7. Final review

• Ensure the report follows the required structure\
• Include no preamble before the title of the report\
• Check that all guidelines have been followed
