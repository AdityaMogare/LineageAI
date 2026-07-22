import type { Diagnostic, DiagnosticKind, Validation } from '../api'

const KIND_LABELS: Partial<Record<DiagnosticKind, string>> = {
  compilation: 'Compilation',
  binder: 'Binder',
  type: 'Type',
  missing_relation: 'Missing relation',
  missing_column: 'Missing column',
  ambiguous_column: 'Ambiguous column',
  syntax: 'Syntax',
  test_failure: 'Test failure',
  runtime: 'Runtime',
  unknown: 'Unknown',
}

function kindLabel(kind: DiagnosticKind): string {
  return KIND_LABELS[kind] ?? 'Unknown'
}

export type ValidationReportProps = {
  validation: Validation | null
  retryCount: number
}

/**
 * Renders the dbt validation outcome for a run: a success banner when
 * `dbt parse` + `dbt build` passed, or the structured diagnostics that the
 * backend error parser extracted when it failed. Also surfaces how many
 * self-corrections the agent needed, since a passing model that took two
 * retries tells a reviewer something different from one that passed cold.
 */
export function ValidationReport({ validation, retryCount }: ValidationReportProps) {
  if (!validation) return null

  return (
    <section
      aria-label="Validation report"
      className="mt-6 rounded-xl border border-slate-700 bg-slate-950/60 p-4"
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="font-mono text-xs uppercase tracking-wider text-cyan-300">
          Validation
        </p>
        <div className="flex items-center gap-2 text-xs">
          <span
            className={
              validation.success
                ? 'rounded-full bg-emerald-400/10 px-3 py-1 font-mono text-emerald-300'
                : 'rounded-full bg-rose-400/10 px-3 py-1 font-mono text-rose-300'
            }
          >
            {validation.success ? 'passed' : 'failed'}
          </span>
          <span className="rounded-full bg-slate-800 px-3 py-1 font-mono text-slate-300">
            {retryCount} {retryCount === 1 ? 'self-correction' : 'self-corrections'}
          </span>
        </div>
      </div>

      <p className="mt-3 font-mono text-xs text-slate-400">
        {validation.command} · {validation.elapsed_seconds.toFixed(1)}s
      </p>

      {validation.success && validation.diagnostics.length === 0 ? (
        <p className="mt-3 text-sm text-emerald-100">
          dbt parse and build completed against the metadata-derived stub tables.
        </p>
      ) : (
        <ul className="mt-3 space-y-3">
          {validation.diagnostics.map((diagnostic, index) => (
            <DiagnosticItem
              diagnostic={diagnostic}
              key={`${diagnostic.kind}-${index}`}
            />
          ))}
        </ul>
      )}
    </section>
  )
}

function DiagnosticItem({ diagnostic }: { diagnostic: Diagnostic }) {
  return (
    <li className="rounded-lg border border-rose-400/20 bg-rose-400/5 p-3">
      <div className="flex flex-wrap items-center gap-2">
        <span className="rounded bg-rose-400/15 px-2 py-0.5 font-mono text-xs text-rose-200">
          {kindLabel(diagnostic.kind)}
        </span>
        {diagnostic.line !== null && (
          <span className="font-mono text-xs text-slate-400">
            line {diagnostic.line}
          </span>
        )}
      </div>
      <p className="mt-2 font-mono text-sm leading-6 text-slate-200">
        {diagnostic.message}
      </p>
      {diagnostic.suggestion && (
        <p className="mt-2 text-sm text-amber-200/90">
          Suggestion: {diagnostic.suggestion}
        </p>
      )}
    </li>
  )
}
