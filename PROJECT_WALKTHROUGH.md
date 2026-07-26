# InsightLens Project Walkthrough

This document is a simple explanation of the project so you can quickly understand it before recording the demo.

## 1. What This Project Is

InsightLens is a multimodal RAG application.

RAG means Retrieval-Augmented Generation. Instead of asking the AI to answer from general memory, the system first retrieves relevant evidence from the uploaded files, then asks the AI to answer using that evidence.

Multimodal means the system can work with more than plain text. It can process:

- PDF files
- DOCX files
- Images such as PNG, JPG, JPEG, BMP, TIF, and TIFF
- Text inside documents
- Tables
- Figures, charts, screenshots, and other visual content

The main idea:

1. The user uploads a file.
2. The backend extracts text and visual evidence from the file.
3. The extracted content is converted into embeddings.
4. The embeddings are stored in ChromaDB.
5. When the user asks a question, the system retrieves the most relevant chunks.
6. OpenAI generates an answer grounded in those retrieved sources.
7. The frontend shows the answer and the evidence sources.

## 2. Project Name

The app name is:

InsightLens

The subtitle is:

Multimodal RAG for Intelligent Document Exploration

## 3. Team Members

- Hamza Obaid
- Walid Alsafadi
- Ameer Alzerei

The team names are stored in:

```text
frontend/src/data/team.ts
```

## 4. Main Technologies

Backend:

- Python 3.12.7
- FastAPI
- Uvicorn
- OpenAI Responses API
- ChromaDB
- Sentence Transformers local embeddings
- LlamaIndex text chunking
- PyPDF2
- pdfplumber
- pdf2image
- python-docx
- Pillow

Frontend:

- Vite
- React
- TypeScript
- Tailwind CSS
- Cairo font
- React Router
- Lucide icons
- Sonner notifications

## 5. Project Structure

```text
multimodal-rag-assistant/
  backend/
    main.py
    config.py
    utils/
      document_processor.py
      rag_engine.py

  frontend/
    src/
      pages/
        LandingPage.tsx
        AssistantPage.tsx
      lib/
        api.ts
      types/
        api.ts
      data/
        team.ts
      App.tsx
      main.tsx
      index.css
    package.json
    vite.config.ts

  tests/
    test_api.py

  README.md
  PROJECT_WALKTHROUGH.md
  requirements.txt
  run_backend.cmd
  run_frontend.cmd
  .env.example
```

## 6. Backend Files Explained

### `backend/main.py`

This is the FastAPI application.

It defines the API endpoints used by the frontend:

- `GET /health`
- `POST /upload`
- `GET /documents`
- `POST /ask`
- `DELETE /documents/{document_id}`
- `DELETE /documents`

It also handles upload validation, document tracking, secure filename handling, and error responses.

### `backend/config.py`

This file stores configuration values such as:

- OpenAI model name
- upload size limit
- allowed file types
- chunk size
- number of retrieved results
- visual PDF page limit
- CORS frontend origin

The values can be controlled using environment variables in `.env`.

### `backend/utils/document_processor.py`

This file is responsible for extracting information from uploaded files.

For PDFs, it extracts:

- Page text
- Tables using `pdfplumber`
- Visual page descriptions by rendering pages as images and sending them to OpenAI vision

For DOCX files, it extracts:

- Paragraph text
- Tables
- Embedded images

For image files, it extracts:

- Visual descriptions
- Visible text through OpenAI vision-based OCR

Important point for the doctor:

The project has OCR-style extraction through OpenAI vision. It does not use a traditional local OCR engine like Tesseract. Instead, images and rendered PDF pages are analyzed by the vision model, which can read visible text and understand charts, figures, and tables.

### `backend/utils/rag_engine.py`

This file handles the RAG logic.

It:

1. Splits extracted text and visual descriptions into chunks.
2. Creates local embeddings using `BAAI/bge-small-en-v1.5`.
3. Stores embeddings in ChromaDB.
4. Retrieves relevant chunks when the user asks a question.
5. Sends only the retrieved evidence to OpenAI.
6. Returns the answer and source list to the frontend.

## 7. Frontend Files Explained

### `frontend/src/pages/LandingPage.tsx`

This is the first page users see.

It introduces the project and gives access to the assistant workspace.

### `frontend/src/pages/AssistantPage.tsx`

This is the main app page.

It includes:

- File upload area
- Uploaded documents list
- Question input
- Answer display
- Source evidence cards
- Loading states
- Delete and clear actions

### `frontend/src/lib/api.ts`

This file contains the frontend API client.

It sends requests to the backend using:

```text
VITE_API_BASE_URL
```

Default backend URL:

```text
http://localhost:8000
```

### `frontend/src/index.css`

This file contains the main styling and imports the Cairo font.

## 8. How Upload Works

When the user uploads a file:

1. The frontend sends the file to `POST /upload`.
2. The backend validates file size, extension, and file content.
3. The backend saves the file using a safe internal UUID filename.
4. The document processor extracts text, tables, and visual evidence.
5. The RAG engine rebuilds the vector index.
6. The frontend shows the uploaded document and extracted evidence count.

The loading messages in the frontend are real waiting states, but they are not exact progress percentages. The backend currently processes the upload as one request, so the frontend cannot know the exact internal step unless we add progress events later.

## 9. How Asking Questions Works

When the user asks a question:

1. The frontend sends the question to `POST /ask`.
2. The backend searches ChromaDB for relevant evidence.
3. It gives the retrieved evidence to OpenAI.
4. OpenAI creates a grounded answer.
5. The backend returns the answer and sources.
6. The frontend displays the answer and source cards.

Each answer is grounded in uploaded documents, not general internet search.

## 10. OCR Explanation

If the doctor asks whether the project has OCR, the best answer is:

The project supports OCR-style extraction using OpenAI vision. Uploaded images, embedded DOCX images, and rendered PDF pages are analyzed by the vision model to extract visible text and describe visual content. This helps the system answer questions about figures, charts, tables, screenshots, and scanned-looking pages.

Important distinction:

- Traditional OCR: Tesseract, EasyOCR, PaddleOCR
- Our project: OpenAI vision-based OCR and visual understanding

This is useful because the model can understand both text and layout, not only raw characters.

## 11. Security Improvements We Added

The project was reviewed with security in mind.

Important protections:

- API keys stay only in backend `.env`.
- `.env` is ignored by git.
- The frontend does not receive the OpenAI API key.
- Upload extensions are restricted.
- Upload file size is limited.
- Uploaded filenames are sanitized.
- Files are stored using UUID internal names.
- The backend avoids exposing internal paths or secrets in user-facing errors.
- CORS is limited to the local frontend origin.
- The number of active documents is limited.
- Visual PDF processing is capped to avoid excessive API cost.
- No hardcoded API keys are committed.

## 12. Cost Control

To avoid wasting OpenAI credits:

- The app uses `gpt-4o-mini`.
- Embeddings are local and free.
- Only retrieved chunks are sent to OpenAI when answering.
- Visual PDF page analysis is limited by `MAX_VISUAL_PDF_PAGES`.
- If OpenAI quota or billing fails, the backend stops inefficient repeated visual calls.

## 13. Environment Variables

Create a root `.env` file using `.env.example`.

Minimum required:

```text
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-4o-mini
OPENAI_IMAGE_DETAIL=high
```

Common optional values:

```text
MAX_UPLOAD_MB=20
MAX_VISUAL_PDF_PAGES=20
FRONTEND_ORIGIN=http://localhost:5173
```

Frontend environment file:

```text
frontend/.env.local
```

It should contain:

```text
VITE_API_BASE_URL=http://localhost:8000
```

## 14. How To Run The Project

Use two terminals.

### Terminal 1: Backend

From the project root:

```powershell
C:\Users\Walid\anaconda3\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

Backend URL:

```text
http://localhost:8000
```

Health check:

```text
http://localhost:8000/health
```

### Terminal 2: Frontend

From the project root:

```powershell
cd frontend
npm run dev
```

Frontend URL:

```text
http://localhost:5173
```

## 15. What To Show In The Recording

Recommended demo flow:

1. Start the backend.
2. Start the frontend.
3. Open the landing page.
4. Go to the assistant workspace.
5. Upload a PDF with text, figures, or tables.
6. Ask for a summary.
7. Ask about a figure.
8. Ask about a table.
9. Show the source cards under the answer.
10. Upload an image and ask what is inside it.
11. Show that the answer is based on uploaded content.
12. Delete or clear documents to show document management.

Good demo questions:

```text
Summarize the uploaded content.
```

```text
What is shown in Figure 2?
```

```text
Extract the table entries.
```

```text
Explain the visual content.
```

```text
What information is available in the first figure?
```

## 16. What To Say In The Recording

Simple explanation:

This project is a multimodal RAG assistant. It allows users to upload documents and images, then ask questions about them. The backend extracts text, tables, and visual evidence. The content is embedded locally and stored in ChromaDB. When the user asks a question, the system retrieves the most relevant evidence and sends it to OpenAI to generate a grounded answer. The frontend displays both the answer and the source evidence, so the user can see where the answer came from.

For OCR:

The system supports OCR-style visual extraction using OpenAI vision. Instead of only reading embedded PDF text, it can render PDF pages and analyze images to understand visible text, figures, charts, and tables.

For security:

The OpenAI API key is stored only on the backend. Uploads are validated, file size is limited, filenames are sanitized, and internal errors do not expose secrets.

## 17. Testing

Backend tests:

```powershell
C:\Users\Walid\anaconda3\python.exe -m pytest
```

Frontend lint:

```powershell
cd frontend
npm run lint
```

Frontend production build:

```powershell
cd frontend
npm run build
```

These were passing during finalization.

## 18. Important Limitations

Be honest about these if asked:

- Documents are stored for the current backend session.
- The app does not include login or user accounts.
- Visual analysis requires OpenAI API credit.
- PDF visual analysis is capped for cost control.
- The project uses OpenAI vision-based OCR, not a separate offline OCR engine.

## 19. Final Status

The project is prepared as a FastAPI plus React multimodal RAG application.

The main completed improvements are:

- Replaced the older backend approach with FastAPI and Uvicorn.
- Replaced the old frontend with a Vite React interface.
- Added multimodal document processing.
- Added PDF text, table, and visual extraction.
- Added image and DOCX visual handling.
- Added local embeddings with ChromaDB.
- Added source-grounded answers.
- Added upload security protections.
- Added frontend polish with Cairo font.
- Added tests and documentation.
