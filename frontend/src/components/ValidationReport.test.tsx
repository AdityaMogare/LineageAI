import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import type { Validation } from '../api'
import { ValidationReport } from './ValidationReport'

const passing: Validation = {
  success: true,
  command: 'dbt parse && dbt build',
  stdout: '',
  stderr: '',
  diagnostics: [],
  elapsed_seconds: 4.2,
}

const failing: Validation = {
  success: false,
  command: 'dbt build',
  stdout: '',
  stderr: '',
  diagnostics: [
    {
      kind: 'missing_column',
      message: 'Referenced column "regoin" not found in table orders',
      line: 7,
      suggestion: 'Did you mean "region"?',
    },
    {
      kind: 'test_failure',
      message: 'not_null test failed for customer_id',
      line: null,
      suggestion: null,
    },
  ],
  elapsed_seconds: 2.8,
}

describe('ValidationReport', () => {
  it('renders nothing before a validation result exists', () => {
    const { container } = render(
      <ValidationReport validation={null} retryCount={0} />,
    )

    expect(container).toBeEmptyDOMElement()
  })

  it('shows a success summary with command and retry count', () => {
    render(<ValidationReport validation={passing} retryCount={0} />)

    expect(screen.getByText('passed')).toBeInTheDocument()
    expect(screen.getByText('0 self-corrections')).toBeInTheDocument()
    expect(screen.getByText(/dbt parse && dbt build/)).toBeInTheDocument()
    expect(screen.getByText(/completed against the metadata/i)).toBeInTheDocument()
  })

  it('lists diagnostics with kind, line, message, and suggestion', () => {
    render(<ValidationReport validation={failing} retryCount={2} />)

    expect(screen.getByText('failed')).toBeInTheDocument()
    expect(screen.getByText('2 self-corrections')).toBeInTheDocument()
    expect(screen.getByText('Missing column')).toBeInTheDocument()
    expect(screen.getByText('line 7')).toBeInTheDocument()
    expect(
      screen.getByText(/Referenced column "regoin" not found/),
    ).toBeInTheDocument()
    expect(screen.getByText(/Did you mean "region"\?/)).toBeInTheDocument()
    expect(screen.getByText('Test failure')).toBeInTheDocument()
    expect(
      screen.getByText(/not_null test failed for customer_id/),
    ).toBeInTheDocument()
  })

  it('uses singular wording for one self-correction', () => {
    render(<ValidationReport validation={passing} retryCount={1} />)

    expect(screen.getByText('1 self-correction')).toBeInTheDocument()
  })
})
