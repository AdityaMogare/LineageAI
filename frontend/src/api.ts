/**
 * Mirrors `ValidationErrorKind` in `backend/src/lineageai/models.py`.
 * Unknown kinds fall back to neutral styling in the UI, so a new backend
 * kind never breaks rendering.
 */
export type DiagnosticKind =
  | 'compilation'
  | 'binder'
  | 'type'
  | 'missing_relation'
  | 'missing_column'
  | 'ambiguous_column'
  | 'syntax'
  | 'test_failure'
  | 'runtime'
  | 'unknown'

export type Diagnostic = {
  kind: DiagnosticKind
  message: string
  line: number | null
  suggestion: string | null
}

/** Mirrors `ValidationResult` in `backend/src/lineageai/models.py`. */
export type Validation = {
  success: boolean
  command: string
  stdout: string
  stderr: string
  diagnostics: Diagnostic[]
  elapsed_seconds: number
}

export type AgentRun = {
  id: string
  prompt: string
  status: string
  retry_count: number
  draft: {
    name: string
    sql: string
    schema_yml: string
    input_datasets: string[]
    explanation: string
  } | null
  validation: Validation | null
  feedback: string | null
  publication: Record<string, unknown> | null
}

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as {
      detail?: string
    } | null
    throw new Error(body?.detail ?? `Request failed (${response.status})`)
  }
  return response.json() as Promise<T>
}

export function createRun(prompt: string): Promise<AgentRun> {
  return request('/api/runs', {
    method: 'POST',
    body: JSON.stringify({ prompt }),
  })
}

export function reviewRun(
  runId: string,
  approved: boolean,
  feedback?: string,
): Promise<AgentRun> {
  return request(`/api/runs/${runId}/review`, {
    method: 'POST',
    body: JSON.stringify({ approved, feedback: feedback || null }),
  })
}
