Develop an agent-powered AI note-taking app using LangGraph, designed for personal productivity and as a demonstration of your skills in computer vision, multi-agent systems, and end-to-end AI engineering. The app will facilitate capturing handwritten notes, automatically formatting them (including complex content like equations and diagrams), classifying content into the correct Notion section, and uploading the processed notes with rich formatting. The goal is to implement a Minimum Viable Product (MVP) capable of image-to-text conversion and formatting within two weeks.

**Core Features**
**Image Capture:**
Capture pictures of handwritten notes via a user interface (LangGraph's prebuilt UI, accessible from PC).
**English Handwriting Recognition:**
Automatically extract typed text (including digits, equations, and diagrams) from handwritten pictures using cutting-edge OCR. you should search for best open source(free) ocr engine for python. Equation must be also in Latex format.
**Formatting & Structuring:**
Clean and format extracted notes (markdown, LaTeX for equations, code blocks, etc.).
Detect and separate sections; classify content to either add as a new Notion sub-page/page or merge with an existing page.
The diagram can be either a flowchart or a block diagram. they must editable
**Integration with Notion:**
Upload formatted notes programmatically into Notion, preserving structure and style. it must use Notion integration API key for authentication and access to Notion's database. I will mcp server for this.

**Agentic Orchestration:**
Use a multi-agent system in LangGraph for more information -'https://docs.oap.langchain.com/quickstart':
Agent 1: Image-to-text extraction (OCR, diagram/equation recognition)
Agent 2: Text cleanup, markdown formatting, and Notion posting
**PC Interaction:**
Leverage LangGraph's prebuilt UI for smooth agent interaction from a PC browser, more information about open agent platform for ui 'https://docs.oap.langchain.com/quickstart'.
**Python First:**
Entire codebase written in Python, using established libraries for AI, vision, and web connectivity.
