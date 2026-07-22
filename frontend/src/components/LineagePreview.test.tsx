import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { LineagePreview } from './LineagePreview'

describe('LineagePreview', () => {
  it('renders nothing without input datasets', () => {
    const { container } = render(
      <LineagePreview modelName="customer_revenue" inputDatasets={[]} />,
    )

    expect(container).toBeEmptyDOMElement()
  })

  it('draws each input table and the generated model', () => {
    render(
      <LineagePreview
        modelName="customer_revenue"
        inputDatasets={['orders', 'customers']}
      />,
    )

    expect(screen.getByText('orders')).toBeInTheDocument()
    expect(screen.getByText('customers')).toBeInTheDocument()
    expect(screen.getByText('customer_revenue')).toBeInTheDocument()
    expect(
      screen.getByRole('img', {
        name: /orders, customers feed customer_revenue/i,
      }),
    ).toBeInTheDocument()
  })

  it('draws one edge per input dataset', () => {
    const { container } = render(
      <LineagePreview
        modelName="wide_model"
        inputDatasets={['a', 'b', 'c', 'd', 'e']}
      />,
    )

    const edges = container.querySelectorAll('path[marker-end]')
    expect(edges).toHaveLength(5)
  })

  it('grows the canvas height with the number of inputs', () => {
    const single = render(
      <LineagePreview modelName="m" inputDatasets={['one']} />,
    )
    const singleHeight = Number(
      single.container.querySelector('svg')?.getAttribute('viewBox')?.split(' ')[3],
    )
    single.unmount()

    const many = render(
      <LineagePreview modelName="m" inputDatasets={['one', 'two', 'three']} />,
    )
    const manyHeight = Number(
      many.container.querySelector('svg')?.getAttribute('viewBox')?.split(' ')[3],
    )

    expect(manyHeight).toBeGreaterThan(singleHeight)
  })

  it('falls back to generated_model when the name is empty', () => {
    render(<LineagePreview modelName="" inputDatasets={['orders']} />)

    expect(screen.getByText('generated_model')).toBeInTheDocument()
  })

  it('shows the DataHub write-back note only when requested', () => {
    const { rerender } = render(
      <LineagePreview modelName="m" inputDatasets={['orders']} />,
    )

    expect(screen.queryByText(/written back to DataHub/i)).not.toBeInTheDocument()

    rerender(
      <LineagePreview modelName="m" inputDatasets={['orders']} showDatahubNote />,
    )

    expect(screen.getByText(/written back to DataHub/i)).toBeInTheDocument()
  })
})
