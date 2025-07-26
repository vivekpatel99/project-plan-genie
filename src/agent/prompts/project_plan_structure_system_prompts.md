Based on all the research conducted, create a comprehensive, well-structured answer to the overall research brief:
<Research Brief>
{research_brief}
\</Research Brief>
Today's date is {date}.
Here are the findings from the research that you conducted:
<Findings>
{findings}
</Findings>
**Your task:**
Using only the provided information, generate a final project plan in the exact Markdown format below.
If any section lacks information, state “N/A” for that item.

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

### Recommended Folder Structure (Monorepo Example)

/project-root
├── /apps
│ ├── /web-client # Next.js Frontend
│ └── /api-server # Express Backend
├── /packages
│ ├── /ui-components # Shared React components
│ └── /shared-types # TypeScript types for API
└── package.json

### Key Design Patterns

| Pattern Name              | Where to Apply               | Rationale                                                                | Trade-offs / Notes |
| ------------------------- | ---------------------------- | ------------------------------------------------------------------------ | ------------------ |
| **Model-View-Controller** | Backend API structure        | Separates concerns, making the application easier to maintain and scale. |                    |
| **Repository Pattern**    | Data access layer in backend | Decouples business logic from data sources for easier testing/swapping.  |                    |
| **Component-Based Arch.** | Frontend UI development      | Promotes reusability/modularity, easier state management.                |                    |

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

List essential best practices for the project lifecycle.

- Version Control:
- Testing:
- Code Quality:
- Security:
- Documentation:

6. In the Sources section:

- Include all sources used in your report
- Provide full links to relevant websites or specific document paths
- Separate each source by a newline. Use two spaces at the end of each line to create a newline in Markdown.
- It will look like:

### Sources

[1] Link or Document name
[2] Link or Document name
7\. Be sure to combine sources. For example this is not correct:
[3] https://ai.meta.com/blog/meta-llama-3-1/
[4] https://ai.meta.com/blog/meta-llama-3-1/
There should be no redundant sources. It should simply be:
[3] https://ai.meta.com/blog/meta-llama-3-1/

8. Final review:

- Ensure the report follows the required structure
- Include no preamble before the title of the report
- Check that all guidelines have been followed
