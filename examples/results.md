# Project Blueprint: AI Note-Taking MVP with LangGraph, Computer Vision, and Agentic Multi-OCR-to-Notion Workflow

## 1. Executive Summary

This project aims to develop a Python-based, agent-powered AI note-taking application focused on personal productivity. Leveraging LangGraph's cognitive agent orchestration with a prebuilt UI, the system enables users to upload multiple handwritten note images via a web interface. The backend employs state-of-the-art open-source computer vision models to extract typed text, complex content such as equations as LaTeX, and images/diagrams. Extracted content is structured and formatted as Markdown, then programmatically uploaded to Notion using the official API, preserving the logical content organization within a flat page. This MVP demonstrates expertise in modular design, multi-agent orchestration, and seamless tool integration, setting a solid foundation for advanced automation and future multi-user capability.

## 2. Technology Stack Recommendation

| Category           | Technology / Framework | Justification                                                                                                    | Trade-offs / Limitations                                         |
| ------------------ | ---------------------- | ---------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------- |
| **Frontend**       | LangGraph prebuilt UI  | Out-of-the-box user interaction via browser; simplifies agent-user interface setup.                              | Limited to provided UI features by LangGraph.                    |
| **Backend**        | Python + LangGraph     | Python for ecosystem and rapid prototyping; LangGraph for multi-agent orchestration and control flow management. | Python slower than compiled languages; LangGraph still evolving. |
| **Database**       | N/A                    | Single-user, stateless MVP stores data in Notion (no secondary backend DB needed).                               | Notion API limitations for direct bulk uploads.                  |
| **Deployment**     | Local server / Docker  | Ensures reproducibility; easy localhost testing; Docker enables later deployment scalability.                    | No cloud deploy; future production requires more.                |
| **Authentication** | Notion API Integration | Uses Notion’s OAuth/token for single-user proof-of-concept integration.                                          | No multi-user handling at MVP; hardcoded tokens.                 |

**OCR Engine Detail:**

- **Typed & Handwritten Text:** PaddleOCR (high accuracy, handwriting support)
- **Equations (LaTeX):** Pix2tex (LaTeX-OCR, state-of-the-art for equation image → LaTeX)
- **Diagrams/Embedded Images:** Embedded as PNG/JPEG; no OCR or captioning needed.

## 3. Project Structure & Architectural Patterns

### Recommended Folder Structure

```
/project-root
├── /ocr_agents
│   ├── text_agent.py  # Uses PaddleOCR for general text, handwriting
│   ├── equation_agent.py  # Uses pix2tex for image-to-LaTeX
│   ├── image_agent.py  # Handles image extraction/embedding
├── /agents
│   ├── workflow_agent.py # LangGraph agent to orchestrate OCR, formatting, Notion upload
│   └── notion_agent.py # Manages Notion API interactions, formatting, error handling
├── /notion
│   ├── markdown_to_notion.py # Markdown → Notion block builder
│   └── notion_api.py
├── /ui
│   └── langgraph_ui.py  # Web interface via LangGraph prebuilt UI
├── /tests
│   ├── test_ocr.py
│   ├── test_notion.py
│   └── test_integration.py
├── /data
│   └── /sample_images
├── requirements.txt
└── README.md
```

### Key Design Patterns

| Pattern Name                     | Where to Apply                     | Rationale                                                                                       | Trade-offs / Notes                              |
| -------------------------------- | ---------------------------------- | ----------------------------------------------------------------------------------------------- | ----------------------------------------------- |
| **Separation of Concerns (SoC)** | All core folders/modules           | Simplifies module responsibility, enables clearer maintenance and expansion.                    | N/A                                             |
| **Modular Design**               | Each OCR/content agent, Notion API | Each function (text, equation, image) is encapsulated; improves testability and upgrades.       | Requires disciplined project management.        |
| **Agent-Oriented Orchestration** | LangGraph workflow_agent           | Empowers composability—allows re-use, intelligent task routing, and scalable future automation. | Increased complexity for agent comms/debugging. |

## 4. Phased Development Plan (MVP to Full Launch)

### **Phase 1: Minimum Viable Product (MVP)**

- [ ] **Feature:** Upload multiple handwritten note images via browser using LangGraph UI
- [ ] **Feature:** OCR pipeline using PaddleOCR for text and handwriting
- [ ] **Feature:** Extract equations into LaTeX via pix2tex
- [ ] **Feature:** Extract and embed non-text images as Markdown image references
- [ ] **Feature:** Markdown formatting of extracted content (sections, equations, images)
- [ ] **Feature:** Programmatic upload of content into Notion as a flat single page (using Notion API, Markdown converted to Notion blocks)
- [ ] **Chore:** Local Notion API integration and testing (token setup, error handling)
- [ ] **Chore:** Unit/integration tests for OCR, Markdown, Notion upload
- [ ] **Chore:** Initial documentation (README, quick-start)

### **Phase 2: Core Features (V1.0)**

- [ ] **Feature:** Improved error handling/reporting for OCR/Notion failures (graceful user messaging)
- [ ] **Feature:** Custom block and markdown mapping to enhance formatting fidelity in Notion
- [ ] **Feature:** Batch-processing performance optimization
- [ ] **Chore:** Expand test coverage (edge cases, large image sets)
- [ ] **Chore:** Dockerization and deployment scripts

### **Phase 3: Advanced Features (V1.1+)**

- [ ] **Feature:** Optional: Per-section page splitting in Notion; basic multi-user support and authentication flow
- [ ] **Feature:** Support for Table recognition and advanced embedded content
- [ ] **Feature:** Cloud deployment (Heroku, AWS, etc.)
- [ ] **Feature:** Analytics dashboard (usage, error rates)

## 5. Key Best Practices

- **Version Control:** Use git; branches for features/bugfixes, enforce PR reviews.
- **Testing:** Unit tests for agents, OCR, and Notion modules; integration tests for end-to-end pipeline.
- **Code Quality:** Follow PEP8; modular structure; consistent naming conventions as per Python best practices; code linting.
- **Security:** Secure Notion API token storage (local env for MVP, vault/secrets manager for prod); sanitize image/markdown inputs.
- **Documentation:** Up-to-date README, code docstrings, inline comments, setup guides; architecture and agent flow diagrams.

### Sources

[1] https://www.datacamp.com/tutorial/langgraph-tutorial\
[2] https://getstream.io/blog/xai-python-multi-agent/\
[3] https://paddlepaddle.github.io/PaddleOCR/main/en/index.html\
[4] https://github.com/lukas-blecher/LaTeX-OCR\
[5] https://developers.notion.com/\
[6] https://medium.com/@ken_lin/langgraph-a-framework-for-building-stateful-multi-agent-llm-applications-a51d5eb68d03\
[7] https://www.goinsight.ai/blog/markdown-to-notion/\
[8] https://medium.com/@khotijahs1/harnessing-the-power-of-paddleocr-for-optical-character-recognition-51427cef5e0b\
[9] https://community.make.com/t/how-do-i-get-markdown-formatted-text-content-into-notion/27379\
[10] https://langchain-ai.github.io/langgraph/cloud/how-tos/generative_ui_react/\
[11] https://novedge.com/blogs/design-news/modular-design-software-architecture-enhancing-customization-scalability-and-collaboration-in-modern-workflows?srsltid=AfmBOor0WwNV9u_9Ntsj2JIkMoB12NENj98NCuI-9SQHS0DJh30uUDH\
[12] https://vfunction.com/blog/modular-software/\
[13] https://nalexn.github.io/separation-of-concerns/\
[14] https://developers.notion.com/reference/request-limits\
[15] https://docs.python-guide.org/writing/structure/\
[16] https://www.python-engineer.com/posts/notion-api-python/\
[17] https://medium.com/@adityamahajan.work/easyocr-a-comprehensive-guide-5ff1cb850168\
[18] https://medium.com/geekculture/tesseract-ocr-understanding-the-contents-of-documents-beyond-their-text-a98704b7c655\
[19] https://packaging.python.org/tutorials/packaging-projects/
