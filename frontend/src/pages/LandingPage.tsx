import { ArrowRight, Database, FileUp, MessageSquareText, Search, Server, Sparkles } from 'lucide-react';
import { Link } from 'react-router-dom';
import { teamMembers } from '../data/team';

const stack = ['Vite and React', 'FastAPI', 'OpenAI', 'LlamaIndex', 'ChromaDB', 'Hugging Face embeddings'];

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-slate-50 text-ink">
      <header className="sticky top-0 z-10 border-b border-slate-200 bg-white/95">
        <nav className="mx-auto flex max-w-6xl items-center justify-between px-5 py-4">
          <Link to="/" className="text-xl font-semibold">InsightLens</Link>
          <div className="hidden items-center gap-6 text-sm text-slate-600 md:flex">
            <a href="#how-it-works">How It Works</a>
            <a href="#technology">Technology</a>
            <a href="#team">Team</a>
          </div>
          <Link className="btn-primary" to="/assistant">
            Open Assistant <ArrowRight size={18} />
          </Link>
        </nav>
      </header>

      <main>
        <section className="mx-auto grid max-w-6xl gap-10 px-5 pb-16 pt-16 lg:grid-cols-[1.05fr_0.95fr] lg:items-center">
          <div>
            <p className="mb-4 text-sm font-semibold uppercase tracking-wide text-accent">Multimodal document exploration</p>
            <h1 className="max-w-3xl text-5xl font-semibold leading-tight text-ink md:text-6xl">
              Understand Documents Beyond Text
            </h1>
            <p className="mt-6 max-w-2xl text-lg leading-8 text-slate-600">
              Upload PDFs and images, then explore their textual and visual content through multimodal retrieval-augmented generation.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link className="btn-primary" to="/assistant">Open Assistant <MessageSquareText size={18} /></Link>
              <a className="btn-secondary" href="#how-it-works">How It Works</a>
            </div>
          </div>
          <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
            <div className="grid gap-4">
              {[
                ['PDF page evidence', 'Page-aware text and visual descriptions'],
                ['Semantic retrieval', 'Local embeddings with ChromaDB'],
                ['Grounded answers', 'Responses generated only from retrieved context'],
              ].map(([title, body]) => (
                <div className="rounded-md border border-slate-200 p-4" key={title}>
                  <p className="font-semibold">{title}</p>
                  <p className="mt-1 text-sm text-slate-600">{body}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section id="how-it-works" className="border-y border-slate-200 bg-white py-16">
          <div className="mx-auto max-w-6xl px-5">
            <h2 className="section-title">How It Works</h2>
            <div className="mt-8 grid gap-5 md:grid-cols-3">
              {[
                [FileUp, 'Upload', 'Add PDF, DOCX, and image files for session-based analysis.'],
                [Sparkles, 'Process', 'Extract text and describe visual pages or images.'],
                [Search, 'Ask', 'Retrieve evidence and generate concise grounded answers.'],
              ].map(([Icon, title, body]) => (
                <article className="feature-card" key={title as string}>
                  <Icon size={24} className="text-accent" />
                  <h3>{title as string}</h3>
                  <p>{body as string}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section id="technology" className="mx-auto max-w-6xl px-5 py-16">
          <h2 className="section-title">Technology</h2>
          <div className="mt-8 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {stack.map((item) => (
              <div className="flex items-center gap-3 rounded-md border border-slate-200 bg-white p-4 shadow-sm" key={item}>
                {item.includes('FastAPI') || item.includes('OpenAI') ? <Server size={20} /> : <Database size={20} />}
                <span className="font-medium">{item}</span>
              </div>
            ))}
          </div>
        </section>

        <section id="team" className="border-y border-slate-200 bg-white py-16">
          <div className="mx-auto max-w-6xl px-5">
            <h2 className="section-title">Team</h2>
            <div className="mt-8 grid gap-4 md:grid-cols-3">
              {teamMembers.map((member) => (
                <div className="rounded-md border border-slate-200 p-5" key={member.name}>
                  <p className="font-semibold">{member.name}</p>
                  <p className="mt-1 text-sm text-slate-600">{member.role}</p>
                </div>
              ))}
            </div>
          </div>
        </section>
      </main>
      <footer className="mx-auto max-w-6xl px-5 py-8 text-sm text-slate-500">
        InsightLens course project.
      </footer>
    </div>
  );
}
