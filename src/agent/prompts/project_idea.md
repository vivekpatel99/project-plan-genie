Develop an agent-powered AI note-taking app using LangGraph, designed for personal productivity and as a demonstration of your skills in computer vision, multi-agent systems, and end-to-end AI engineering. The app will facilitate capturing handwritten notes, automatically formatting them (including complex content like equations and diagrams), classifying content into the correct Notion section, and uploading the processed notes with rich formatting. The goal is to implement a Minimum Viable Product (MVP) capable of image-to-text conversion and formatting within two weeks.

**Core Features**
**Image Capture:**
Capture pictures of handwritten notes in English via a user interface (LangGraph's prebuilt UI, accessible from PC). It should capture image one by one. I would like to build monolith architecture, because i want to keep it simple and easy to use.
**English Handwriting Recognition:**
Automatically extract typed text (including digits, equations, and diagrams) from handwritten pictures using cutting-edge OCR. you should search for best open source(free) ocr engine for python. Equation must be also in Latex format. You must find best open source OCR engine for this task
**Formatting & Structuring:**
Clean and format extracted notes (markdown, LaTeX for equations, code blocks, etc.).
Detect and separate sections; classify content to either add as a new Notion sub-page/page or merge with an existing page.
The diagram can be either a flowchart or a block diagram. it must supports tables. Diagram must be editable for user interaction/update.
**Integration with Notion:**
Upload formatted notes programmatically into Notion, preserving structure and style. it must use Notion integration API key (my personal API keys) for authentication and access to Notion's database. I will mcp server for communicating with Notion.

**Agentic Orchestration:**
Use a multi-agent system in LangGraph for more information -'https://docs.oap.langchain.com/quickstart':
Agent 1: Image-to-text extraction (OCR, diagram/equation recognition)
Agent 2: Text cleanup, markdown formatting, and Notion posting
**PC Interaction:**
Leverage LangGraph's prebuilt UI for smooth agent interaction from a PC browser, more information about open agent platform for ui 'https://docs.oap.langchain.com/quickstart'.
**Python First:**
Entire codebase written in Python, using established libraries for AI, vision, and web connectivity.

- you must select clean architecture and SOLID principles and decide where to use which principles for this project
- you must select best testing strategy for this project
- you must decide better architecture style, such as a microservice-style modular backend, a monolith and so on
- use model can be easily swappable to keep up with the latest developments in AI technology
- it is personal project for personal portfolio development so good readme with proper diagram (visualization) is required. so anybody can easily understand your project idea and workflow.
