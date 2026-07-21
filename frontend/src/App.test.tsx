import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import App from './App'

describe('App', () => {
  it('introduces the product', () => {
    render(<App />)

    expect(
      screen.getByRole('heading', { name: /build dbt models with lineage/i }),
    ).toBeInTheDocument()
  })
})
