export type DocumentSummary = {
  id: string;
  filename: string;
  file_type: string;
  pages: number | null;
  text_items: number;
  visual_items: number;
  warnings: string[];
};

export type Source = {
  document_id: string;
  filename: string;
  page: number | null;
  content_type: string;
  snippet: string;
  score: number | null;
};

export type ChatMessage = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  sources?: Source[];
};
