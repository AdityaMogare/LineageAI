import { useState } from 'react'

import { type AgentRun, createRun, reviewRun } from './api'
import { LineagePreview } from './components/LineagePreview'
import { ValidationReport } from './components/ValidationReport'

function App() {
  const [prompt, setPrompt] = useState(
    'Build a customer revenue model by region from orders and customers.',
  )
  const [run, setRun] = useState<AgentRun | null>(null)
  const [feedback, setFeedback] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const pullRequestUrl =
    typeof run?.publication?.pull_request_url === 'string'
      ? run.publication.pull_request_url
      : null

  async function submit() {
    setBusy(true)
    setError('')
    try {
      setRun(await createRun(prompt))
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Unable to start run')
    } finally {
      setBusy(false)
    }
  }

  async function decide(approved: boolean) {
    if (!run) return
    setBusy(true)
    setError('')
    try {
      setRun(await reviewRun(run.id, approved, feedback))
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Unable to review run')
    } finally {
      setBusy(false)
    }
  }

  return (
    <main className="mx-auto min-h-screen max-w-7xl px-6 py-12">
      <header className="mb-12 max-w-4xl">
        <p className="mb-4 font-mono text-sm uppercase tracking-[0.3em] text-cyan-300">
          LineageAI · Metadata-aware development
        </p>
        <h1 className="text-4xl font-semibold tracking-tight text-white md:text-6xl">
          Build dbt models with lineage, not guesses.
        </h1>
        <p className="mt-6 max-w-2xl text-lg leading-8 text-slate-300">
          LineageAI grounds Kimi K3 in DataHub metadata, validates generated SQL
          against DuckDB, and pauses before publishing a reviewed pull request.
        </p>
      </header>

      <section className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)]">
        <div className="rounded-2xl border border-slate-700 bg-slate-900/70 p-6">
          <label
            className="mb-3 block text-sm font-medium text-slate-200"
            htmlFor="request"
          >
            Describe the model
          </label>
          <textarea
            id="request"
            className="min-h-40 w-full resize-y rounded-xl border border-slate-700 bg-slate-950 p-4 text-slate-100 outline-none transition focus:border-cyan-400"
            value={prompt}
            onChange={(event) => setPrompt(event.target.value)}
          />
          <button
            className="mt-4 w-full rounded-xl bg-cyan-400 px-5 py-3 font-semibold text-slate-950 transition hover:bg-cyan-300 disabled:cursor-not-allowed disabled:opacity-50"
            disabled={busy || prompt.trim().length < 5}
            onClick={submit}
            type="button"
          >
            {busy ? 'Running validation…' : 'Generate dbt model'}
          </button>
          {error && (
            <p role="alert" className="mt-4 text-sm text-rose-300">
              {error}
            </p>
          )}
          {run && (
            <div className="mt-6 border-t border-slate-800 pt-5">
              <div className="flex items-center justify-between text-sm">
                <span className="text-slate-400">Status</span>
                <span className="rounded-full bg-cyan-400/10 px-3 py-1 font-mono text-cyan-300">
                  {run.status.replaceAll('_', ' ')}
                </span>
              </div>
              <div className="mt-3 flex items-center justify-between text-sm">
                <span className="text-slate-400">Self-corrections</span>
                <span className="font-mono text-slate-200">{run.retry_count}</span>
              </div>
            </div>
          )}
        </div>

        <div className="min-h-96 rounded-2xl border border-slate-700 bg-slate-900/70 p-6">
          {!run?.draft ? (
            <div className="flex h-full min-h-80 items-center justify-center text-center text-slate-500">
              Generated SQL, tests, and lineage will appear here.
            </div>
          ) : (
            <div>
              <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-xs uppercase tracking-widest text-slate-500">
                    Review candidate
                  </p>
                  <h2 className="mt-1 text-2xl font-semibold text-white">
                    {run.draft.name}
                  </h2>
                </div>
                <div className="flex gap-2">
                  {run.draft.input_datasets.map((dataset) => (
                    <span
                      className="rounded-md border border-slate-700 px-2 py-1 font-mono text-xs text-slate-300"
                      key={dataset}
                    >
                      {dataset}
                    </span>
                  ))}
                </div>
              </div>
              <div className="mb-6">
                <LineagePreview
                  inputDatasets={run.draft.input_datasets}
                  modelName={run.draft.name}
                  showDatahubNote={run.status === 'awaiting_review'}
                />
                <ValidationReport
                  retryCount={run.retry_count}
                  validation={run.validation}
                />
              </div>
              <CodePanel label="SQL" value={run.draft.sql} />
              <CodePanel label="schema.yml" value={run.draft.schema_yml} />
              {run.status === 'awaiting_review' && (
                <div className="mt-6 border-t border-slate-800 pt-6">
                  <label className="text-sm text-slate-300" htmlFor="feedback">
                    Review note (required when rejecting)
                  </label>
                  <textarea
                    id="feedback"
                    className="mt-2 min-h-20 w-full rounded-lg border border-slate-700 bg-slate-950 p-3 text-sm text-slate-100"
                    value={feedback}
                    onChange={(event) => setFeedback(event.target.value)}
                  />
                  <div className="mt-3 flex gap-3">
                    <button
                      className="rounded-lg border border-rose-400/50 px-4 py-2 text-rose-200 disabled:opacity-50"
                      disabled={busy || !feedback.trim()}
                      onClick={() => decide(false)}
                      type="button"
                    >
                      Reject
                    </button>
                    <button
                      className="rounded-lg bg-emerald-400 px-4 py-2 font-semibold text-slate-950 disabled:opacity-50"
                      disabled={busy}
                      onClick={() => decide(true)}
                      type="button"
                    >
                      Approve
                    </button>
                  </div>
                </div>
              )}
              {run.status === 'approved' && (
                <div className="mt-6 rounded-xl border border-emerald-400/30 bg-emerald-400/10 p-4 text-emerald-100">
                  {pullRequestUrl ? (
                    <a
                      className="font-semibold underline"
                      href={pullRequestUrl}
                      rel="noreferrer"
                      target="_blank"
                    >
                      Open generated pull request
                    </a>
                  ) : (
                    <p>Approved. Publishing is disabled until credentials are configured.</p>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </section>
    </main>
  )
}

function CodePanel({ label, value }: { label: string; value: string }) {
  return (
    <div className="mb-4">
      <p className="mb-2 font-mono text-xs uppercase tracking-wider text-cyan-300">
        {label}
      </p>
      <pre className="max-h-72 overflow-auto rounded-xl bg-slate-950 p-4 text-left font-mono text-sm leading-6 text-slate-300">
        <code>{value}</code>
      </pre>
    </div>
  )
}

export default App
