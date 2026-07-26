import { Clipboard, FileImage, FileText, Loader2, MessageSquare, Send, Trash2, Upload, X } from 'lucide-react';
import { FormEvent, useEffect, useMemo, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { Link } from 'react-router-dom';
import remarkGfm from 'remark-gfm';
import { toast } from 'sonner';
import { api } from '../lib/api';
import type { ChatMessage, DocumentSummary } from '../types/api';

const supported = ['.pdf', '.docx', '.png', '.jpg', '.jpeg', '.bmp', '.tif', '.tiff'];
const uploadMessages = [
  'Uploading file to the backend...',
  'Waiting for document processing...',
  'Backend may extract text, analyze visuals, and rebuild the index...',
  'Still processing; large PDFs can take longer...',
];
const suggestions = [
  'Summarize the uploaded content.',
  'What are the main findings?',
  'Explain the visual content.',
  'What information appears on page 3?',
];

export default function AssistantPage() {
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [question, setQuestion] = useState('');
  const [uploading, setUploading] = useState(false);
  const [asking, setAsking] = useState(false);
  const [apiIssue, setApiIssue] = useState('');
  const [dropActive, setDropActive] = useState(false);
  const [statusIndex, setStatusIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const maxSizeText = '20 MB';
  const hasDocuments = documents.length > 0;

  useEffect(() => {
    api
      .health()
      .then(() => api.listDocuments())
      .then((data) => {
        setDocuments(data.documents);
        setApiIssue('');
      })
      .catch(() => setApiIssue('Backend unavailable. Start the FastAPI server and refresh.'));
  }, []);

  useEffect(() => {
    if (!uploading) {
      setStatusIndex(0);
      return;
    }
    const timer = window.setInterval(() => setStatusIndex((value) => (value + 1) % uploadMessages.length), 1800);
    return () => window.clearInterval(timer);
  }, [uploading]);

  const accepted = useMemo(() => supported.join(','), []);

  function addFiles(files: FileList | File[]) {
    const next = Array.from(files);
    const valid = next.filter((file) => supported.some((ext) => file.name.toLowerCase().endsWith(ext)));
    if (valid.length !== next.length) {
      toast.error('Unsupported format. Use PDF, DOCX, PNG, JPG, BMP, or TIFF.');
    }
    setSelectedFiles((current) => [...current, ...valid]);
  }

  async function uploadSelected() {
    if (!selectedFiles.length) return;
    setUploading(true);
    try {
      for (const file of selectedFiles) {
        const result = await api.upload(file);
        setDocuments((current) => [...current.filter((doc) => doc.id !== result.document.id), result.document]);
        if (result.warnings.length) {
          toast.warning(result.warnings.join(' '));
        } else {
          toast.success(`${result.document.filename} is ready.`);
        }
      }
      setSelectedFiles([]);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Upload failed.');
    } finally {
      setUploading(false);
    }
  }

  async function deleteDocument(id: string) {
    try {
      await api.deleteDocument(id);
      setDocuments((current) => current.filter((doc) => doc.id !== id));
      toast.success('Document deleted.');
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Delete failed.');
    }
  }

  async function clearDocuments() {
    try {
      await api.clearDocuments();
      setDocuments([]);
      setMessages([]);
      toast.success('All documents cleared.');
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Clear failed.');
    }
  }

  async function ask(event?: FormEvent, preset?: string) {
    event?.preventDefault();
    const text = (preset ?? question).trim();
    if (!text || asking || !hasDocuments) return;
    const userMessage: ChatMessage = { id: crypto.randomUUID(), role: 'user', content: text };
    setMessages((current) => [...current, userMessage]);
    setQuestion('');
    setAsking(true);
    try {
      const result = await api.ask(text);
      setMessages((current) => [
        ...current,
        { id: crypto.randomUUID(), role: 'assistant', content: result.answer, sources: result.sources },
      ]);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Question failed.';
      setMessages((current) => [...current, { id: crypto.randomUUID(), role: 'assistant', content: message }]);
    } finally {
      setAsking(false);
    }
  }

  return (
    <div className="min-h-screen bg-slate-50 text-ink">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-5 py-4">
          <Link to="/" className="brand-link" aria-label="InsightLens home">
            InsightLens
          </Link>
          <span className="text-sm text-slate-500">Multimodal RAG for Intelligent Document Exploration</span>
        </div>
      </header>

      <main className="mx-auto grid max-w-7xl gap-6 px-5 py-6 lg:grid-cols-[380px_1fr]">
        <aside className="space-y-5">
          <section
            className={`rounded-lg border bg-white p-5 shadow-sm transition ${dropActive ? 'border-accent' : 'border-slate-200'}`}
            onDragOver={(event) => {
              event.preventDefault();
              setDropActive(true);
            }}
            onDragLeave={() => setDropActive(false)}
            onDrop={(event) => {
              event.preventDefault();
              setDropActive(false);
              addFiles(event.dataTransfer.files);
            }}
          >
            <div className="flex items-center justify-between">
              <h2 className="panel-title">Documents</h2>
              <button className="icon-button" aria-label="Choose files" onClick={() => inputRef.current?.click()}>
                <Upload size={18} />
              </button>
            </div>
            <button className="mt-4 w-full rounded-md border border-dashed border-slate-300 p-6 text-center transition hover:border-accent focus:outline-none focus:ring-2 focus:ring-accent" onClick={() => inputRef.current?.click()}>
              <Upload className="mx-auto mb-3 text-accent" />
              <span className="block font-medium">Drop files or browse</span>
              <span className="mt-1 block text-sm text-slate-500">{supported.join(', ')} up to {maxSizeText}</span>
            </button>
            <input ref={inputRef} className="sr-only" type="file" multiple accept={accepted} onChange={(event) => event.target.files && addFiles(event.target.files)} />

            {selectedFiles.length > 0 && (
              <div className="mt-4 space-y-2">
                {selectedFiles.map((file) => (
                  <div className="flex items-center justify-between rounded-md bg-slate-100 px-3 py-2 text-sm" key={`${file.name}-${file.size}`}>
                    <span className="truncate">{file.name}</span>
                    <button className="icon-button" aria-label={`Remove ${file.name}`} onClick={() => setSelectedFiles((items) => items.filter((item) => item !== file))}>
                      <X size={16} />
                    </button>
                  </div>
                ))}
                <button className="btn-primary w-full justify-center" disabled={uploading} onClick={uploadSelected}>
                  {uploading ? <Loader2 className="animate-spin" size={18} /> : <Upload size={18} />}
                  {uploading ? uploadMessages[statusIndex] : 'Upload selected files'}
                </button>
              </div>
            )}
          </section>

          <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex items-center justify-between">
              <h2 className="panel-title">Uploaded Files</h2>
              <button className="icon-button text-red-600" aria-label="Clear all documents" disabled={!documents.length} onClick={clearDocuments}>
                <Trash2 size={18} />
              </button>
            </div>
            {apiIssue && <p className="mt-3 rounded-md bg-red-50 p-3 text-sm text-red-700">{apiIssue}</p>}
            {!documents.length && !apiIssue && <p className="mt-4 rounded-md bg-slate-100 p-4 text-sm text-slate-600">No documents uploaded yet.</p>}
            <div className="mt-4 space-y-3">
              {documents.map((doc) => (
                <article className="rounded-md border border-slate-200 p-3" key={doc.id}>
                  <div className="flex items-start gap-3">
                    {doc.file_type === 'image' ? <FileImage className="mt-1 text-accent" size={20} /> : <FileText className="mt-1 text-accent" size={20} />}
                    <div className="min-w-0 flex-1">
                      <p className="truncate font-medium">{doc.filename}</p>
                      <p className="mt-1 text-xs text-slate-500">
                        {doc.text_items} text evidence · {doc.visual_items} visual evidence{doc.pages ? ` · ${doc.pages} pages` : ''}
                      </p>
                      {doc.warnings.map((warning) => <p className="mt-2 text-xs text-amber-700" key={warning}>{warning}</p>)}
                    </div>
                    <button className="icon-button text-red-600" aria-label={`Delete ${doc.filename}`} onClick={() => deleteDocument(doc.id)}>
                      <Trash2 size={16} />
                    </button>
                  </div>
                </article>
              ))}
            </div>
          </section>
        </aside>

        <section className="flex min-h-[72vh] flex-col rounded-lg border border-slate-200 bg-white shadow-sm">
          <div className="border-b border-slate-200 p-5">
            <h1 className="panel-title">Assistant Workspace</h1>
            <p className="mt-1 text-sm text-slate-500">{hasDocuments ? 'Ask grounded questions about uploaded evidence.' : 'Upload a document to begin.'}</p>
          </div>

          <div className="flex-1 space-y-5 overflow-y-auto p-5">
            {!messages.length && (
              <div className="rounded-lg bg-slate-50 p-6">
                <MessageSquare className="text-accent" />
                <h2 className="mt-3 text-xl font-semibold">Ready when your documents are.</h2>
                <div className="mt-5 grid gap-2 sm:grid-cols-2">
                  {suggestions.map((item) => (
                    <button className="suggestion" disabled={!hasDocuments || asking} key={item} onClick={() => ask(undefined, item)}>
                      {item}
                    </button>
                  ))}
                </div>
              </div>
            )}
            {messages.map((message) => (
              <article className={`chat-message ${message.role === 'user' ? 'chat-user' : 'chat-assistant'}`} key={message.id}>
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
                {message.role === 'assistant' && (
                  <button className="mt-3 inline-flex items-center gap-2 text-sm text-slate-600 hover:text-accent" onClick={() => navigator.clipboard.writeText(message.content)}>
                    <Clipboard size={15} /> Copy answer
                  </button>
                )}
                {message.sources && message.sources.length > 0 && (
                  <details className="mt-4">
                    <summary className="cursor-pointer text-sm font-semibold text-slate-700">Sources</summary>
                    <div className="mt-3 space-y-3">
                      {message.sources.map((source) => (
                        <div className="rounded-md border border-slate-200 p-3 text-sm" key={`${source.document_id}-${source.page}-${source.content_type}-${source.snippet}`}>
                          <div className="flex flex-wrap gap-2 text-xs font-semibold uppercase text-slate-500">
                            <span>{source.filename}</span>
                            {source.page !== null && <span>Page {source.page}</span>}
                            <span>{source.content_type}</span>
                            {source.score !== null && <span>Score {source.score.toFixed(2)}</span>}
                          </div>
                          <p className="mt-2 text-slate-700">{source.snippet}</p>
                        </div>
                      ))}
                    </div>
                  </details>
                )}
              </article>
            ))}
            {asking && (
              <div className="rounded-lg bg-slate-50 p-4 text-sm text-slate-600">
                <Loader2 className="mr-2 inline animate-spin" size={16} /> Retrieving evidence and requesting a grounded answer...
              </div>
            )}
          </div>

          <form className="border-t border-slate-200 p-4" onSubmit={ask}>
            <label className="sr-only" htmlFor="question">Question</label>
            <div className="flex gap-3">
              <input
                id="question"
                className="min-w-0 flex-1 rounded-md border border-slate-300 px-4 py-3 focus:outline-none focus:ring-2 focus:ring-accent"
                value={question}
                disabled={!hasDocuments || asking}
                onChange={(event) => setQuestion(event.target.value)}
                placeholder={hasDocuments ? 'Ask something about your documents...' : 'Upload documents to enable questions'}
              />
              <button className="btn-primary" disabled={!question.trim() || !hasDocuments || asking} type="submit" aria-label="Send question">
                <Send size={18} /> Send
              </button>
            </div>
          </form>
        </section>
      </main>
    </div>
  );
}
