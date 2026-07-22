import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import App from './App'

describe('App', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('introduces the product', () => {
    render(<App />)

    expect(
      screen.getByRole('heading', { name: /build dbt models with lineage/i }),
    ).toBeInTheDocument()
  })

  it('submits, reviews, and approves a generated model', async () => {
    const draft = {
      name: 'customer_revenue',
      sql: 'select customer_id from main.orders',
      schema_yml: 'version: 2',
      input_datasets: ['orders', 'customers'],
      explanation: '',
    }
    const validation = {
      success: true,
      command: 'dbt build',
      stdout: '',
      stderr: '',
      diagnostics: [],
      elapsed_seconds: 3.4,
    }
    const fetchMock = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            id: 'run-1',
            prompt: 'Build customer revenue',
            status: 'awaiting_review',
            retry_count: 1,
            draft,
            validation,
            feedback: null,
            publication: null,
          }),
          { status: 201 },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            id: 'run-1',
            prompt: 'Build customer revenue',
            status: 'approved',
            retry_count: 1,
            draft,
            validation,
            feedback: null,
            publication: null,
          }),
          { status: 200 },
        ),
      )

    render(<App />)
    fireEvent.click(
      screen.getByRole('button', { name: /generate dbt model/i }),
    )

    expect(
      await screen.findByRole('heading', { name: 'customer_revenue' }),
    ).toBeInTheDocument()

    expect(
      screen.getByRole('img', {
        name: /orders, customers feed customer_revenue/i,
      }),
    ).toBeInTheDocument()
    expect(screen.getByText('passed')).toBeInTheDocument()
    expect(screen.getByText('1 self-correction')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Approve' }))

    await waitFor(() => {
      expect(screen.getByText('approved')).toBeInTheDocument()
    })
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })

  it('shows validation diagnostics for a failed run', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          id: 'run-2',
          prompt: 'Build a broken model',
          status: 'failed',
          retry_count: 3,
          draft: {
            name: 'broken_model',
            sql: 'select regoin from main.orders',
            schema_yml: 'version: 2',
            input_datasets: ['orders'],
            explanation: '',
          },
          validation: {
            success: false,
            command: 'dbt build',
            stdout: '',
            stderr: '',
            diagnostics: [
              {
                kind: 'missing_column',
                message: 'Column "regoin" not found',
                line: 1,
                suggestion: 'Did you mean "region"?',
              },
            ],
            elapsed_seconds: 2.1,
          },
          feedback: null,
          publication: null,
        }),
        { status: 201 },
      ),
    )

    render(<App />)
    fireEvent.click(
      screen.getByRole('button', { name: /generate dbt model/i }),
    )

    expect(await screen.findByText('Missing column')).toBeInTheDocument()
    expect(screen.getByText(/Column "regoin" not found/)).toBeInTheDocument()
    expect(screen.getByText(/Did you mean "region"\?/)).toBeInTheDocument()
    expect(screen.getByText('3 self-corrections')).toBeInTheDocument()
  })
})
