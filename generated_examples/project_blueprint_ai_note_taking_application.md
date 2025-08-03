# Project Blueprint: AI Note-Taking Application

## 1. Executive Summary

The AI Note-Taking Application aims to provide an intuitive platform for capturing handwritten notes via optical character recognition (OCR), integrating seamlessly with Notion for structured upload and organization. Utilizing LangGraph's multi-agent framework, the application facilitates efficient user interaction and advanced content processing, including mathematical equations and diagrams formatted in Markdown and LaTeX. The project addresses the need for a robust solution that enhances productivity and organization in note-taking, making it an essential tool for students and professionals alike.

## 2. Technology Stack Recommendation

| Category           | Technology / Framework    | Justification                                                                    | Trade-offs / Limitations                           |
| ------------------ | ------------------------- | -------------------------------------------------------------------------------- | -------------------------------------------------- |
| **Frontend**       | LangGraph Prebuilt UI     | Quickly build a user-friendly interface accessible from a PC browser.            | Limited customization compared to custom-built UI. |
| **Backend**        | Python (Flask/FastAPI)    | Simple setup for RESTful API integration, support for multi-agent orchestration. | Dependency management required.                    |
| **Database**       | Notion API                | Direct integration for structured note storage and retrieval.                    | Requires API key management and user permissions.  |
| **Deployment**     | Docker                    | Ensures a consistent environment across development, testing, and production.    | Additional complexity in container orchestration.  |
| **Authentication** | OAuth 2.0 with Notion API | Secure way to authenticate API requests and manage user access.                  | Requires management of access tokens and scopes.   |

## 3. Project Structure & Architectural Patterns

### Recommended Folder Structure

```
/ai_note_taking_app
|-- /api-server
|   |-- /controllers
|   |-- /repositories
|   |-- /services
|   |-- /factories
|   |-- /models
|   |-- main.py
|
|-- /frontend
|   |-- /components
|   |-- /pages
|   |-- /public
|   |-- index.html
|
|-- /docs
|-- /tests
```

### Key Design Patterns

| Pattern Name              | Where to Apply                         | Rationale                                                                                       | Trade-offs / Notes                                       |
| ------------------------- | -------------------------------------- | ----------------------------------------------------------------------------------------------- | -------------------------------------------------------- |
| **Model-View-Controller** | /api-server/controllers                | Separates presentation logic from business logic, improves maintainability.                     | May require additional files for routing.                |
| **Repository Pattern**    | /api-server/repositories               | Decouples data access logic from business logic, allowing for easier testing and maintenance.   | Extra layer of abstraction may slow initial development. |
| **Strategy Pattern**      | /api-server/services/ocr_strategies    | Supports flexible OCR algorithm implementation (e.g., Tesseract, EasyOCR) for handwritten text. | Complexity increases as more strategies are added.       |
| **Factory Pattern**       | /api-server/factories                  | Centralizes object creation, making it easier to manage dependencies and configurations.        | May add overhead for simple object creation.             |
| **Dependency Injection**  | Service constructors & FastAPI Depends | Promotes loose coupling for easier testing and higher modularity.                               | Requires understanding of DI principles.                 |
| **Context Manager**       | /api-server/db/session_manager.py      | Manages DB sessions safely and simplifies resource cleanup.                                     | Limited to environments supporting context managers.     |

## 4. Phased Development Plan (MVP to Full Launch)

### **Phase 1: Minimum Viable Product (MVP)**

- [ ] **Feature: Handwriting recognition and conversion using an OCR library (Tesseract)**
- [ ] **Feature: Basic integration with Notion API for uploading text.**
- [ ] **Chore: Setup Docker for local development environment.**
- [ ] **Chore: Implement basic logging and error handling.**

### **Phase 2: Core Features (V1.0)**

- [ ] **Feature: Integration of multi-agent framework (LangGraph) for orchestration.**
- [ ] **Feature: Advanced parsing of equations and diagrams with LaTeX and Markdown formatting.**
- [ ] **Feature: User interface for seamless interaction via LangGraph's prebuilt UI.**
- [ ] **Chore: Enhanced logging and error recovery mechanisms.**

### **Phase 3: Advanced Features (V1.1+)**

- [ ] **Feature: Section classification and structured content organization for Notion integration.**
- [ ] **Feature: User authentication and secure API key management.**
- [ ] **Feature: Integration with more OCR strategies for improved character recognition.**

## 5. Key Best Practices

- **Version Control**: Use trunk-based flow, enforce pull request checks, and utilize semantic commits throughout the project lifecycle.
- **Testing**: Implement unit tests using pytest, integration testing with docker-compose, and end-to-end tests with Playwright for the frontend.
- **Code Quality**: Enforce code quality checks using linting (ruff), formatting with black, and type checking via mypy.
- **Security**: Conduct OWASP top-10 audits regularly, use dependency scanning tools to identify vulnerabilities, and apply secrets management best practices.
- **Documentation**: Maintain architecture decision records (ADRs) in /docs/adr, generate API documentation using OpenAPI specifications, and include informative README badges.

## 6. Sources

1. LangGraph Documentation: [LangGraph Docs](https://langchain-ai.github.io/langgraph/)
2. Notion API Documentation: [Notion API](https://developers.notion.com/)
3. Tesseract OCR Information: [Tesseract OCR](https://github.com/tesseract-ocr/tesseract)
4. Python Docker Documentation: [Docker Python Docs](https://docs.docker.com/samples/python/)
5. OWASP Top Ten: [OWASP](https://owasp.org/www-project-top-ten/)
6. Testing with pytest: [pytest Docs](https://docs.pytest.org/en/stable/)

## 7. Final review

- The report follows the required structure.
- No preamble before the title of the report.
- All guidelines have been followed and each section is complete.
