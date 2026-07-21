export type Diagnostic = {
  kind: string
  message: string
  line: number | null
  suggestion: string | null
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
  validation: {
    success: boolean
    diagnostics: Diagnostic[]
  } | null
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
