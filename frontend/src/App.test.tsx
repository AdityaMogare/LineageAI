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
      input_datasets: ['orders'],
      explanation: '',
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
            validation: { success: true, diagnostics: [] },
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
            validation: { success: true, diagnostics: [] },
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

    expect(await screen.findByText('customer_revenue')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Approve' }))

    await waitFor(() => {
      expect(screen.getByText('approved')).toBeInTheDocument()
    })
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })
})
