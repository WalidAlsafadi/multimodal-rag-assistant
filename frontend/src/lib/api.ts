import type { DocumentSummary, Source } from '../types/api';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

type HealthResponse = {
  status: string;
  application: string;
  model: string;
  documents: number;
};

type UploadResponse = {
  document: DocumentSummary;
  warnings: string[];
};

type DocumentsResponse = {
  documents: DocumentSummary[];
};

type AskResponse = {
  answer: string;
  sources: Source[];
};

async function parseResponse<T>(response: Response): Promise<T> {
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.detail ?? 'The API request failed.');
  }
  return data as T;
}

export const api = {
  async health() {
    return parseResponse<HealthResponse>(await fetch(`${API_BASE_URL}/health`));
  },

  async upload(file: File) {
    const form = new FormData();
    form.append('file', file);
    return parseResponse<UploadResponse>(
      await fetch(`${API_BASE_URL}/upload`, {
        method: 'POST',
        body: form,
      }),
    );
  },

  async listDocuments() {
    return parseResponse<DocumentsResponse>(await fetch(`${API_BASE_URL}/documents`));
  },

  async ask(question: string) {
    return parseResponse<AskResponse>(
      await fetch(`${API_BASE_URL}/ask`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question }),
      }),
    );
  },

  async deleteDocument(documentId: string) {
    return parseResponse<{ message: string }>(
      await fetch(`${API_BASE_URL}/documents/${documentId}`, { method: 'DELETE' }),
    );
  },

  async clearDocuments() {
    return parseResponse<{ message: string }>(
      await fetch(`${API_BASE_URL}/documents`, { method: 'DELETE' }),
    );
  },
};
