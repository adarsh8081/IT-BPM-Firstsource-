/**
 * @jest-environment jsdom
 */

import React from 'react'
import { render, screen } from '@testing-library/react'
import ConfidenceBadge from '@/components/ui/ConfidenceBadge'

describe('ConfidenceBadge', () => {
  it('renders high confidence correctly', () => {
    const { container } = render(<ConfidenceBadge score={0.9} />)
    expect(container.firstChild).toMatchSnapshot()
    
    expect(screen.getByLabelText('Confidence score: 90%')).toBeInTheDocument()
    expect(screen.getByText('90%')).toBeInTheDocument()
  })

  it('renders medium confidence correctly', () => {
    const { container } = render(<ConfidenceBadge score={0.65} />)
    expect(container.firstChild).toMatchSnapshot()
    
    expect(screen.getByLabelText('Confidence score: 65%')).toBeInTheDocument()
    expect(screen.getByText('65%')).toBeInTheDocument()
  })

  it('renders low confidence correctly', () => {
    const { container } = render(<ConfidenceBadge score={0.35} />)
    expect(container.firstChild).toMatchSnapshot()
    
    expect(screen.getByLabelText('Confidence score: 35%')).toBeInTheDocument()
    expect(screen.getByText('35%')).toBeInTheDocument()
  })

  it('renders with custom className', () => {
    const { container } = render(
      <ConfidenceBadge score={0.85} className="custom-class" />
    )
    expect(container.firstChild).toMatchSnapshot()
    
    expect(screen.getByLabelText('Confidence score: 85%')).toBeInTheDocument()
  })

  it('applies correct variant classes for high confidence', () => {
    render(<ConfidenceBadge score={0.9} />)
    
    const badge = screen.getByLabelText('Confidence score: 90%')
    expect(badge).toHaveClass('bg-green-100', 'text-green-800')
  })

  it('applies correct variant classes for medium confidence', () => {
    render(<ConfidenceBadge score={0.6} />)
    
    const badge = screen.getByLabelText('Confidence score: 60%')
    expect(badge).toHaveClass('bg-yellow-100', 'text-yellow-800')
  })

  it('applies correct variant classes for low confidence', () => {
    render(<ConfidenceBadge score={0.3} />)
    
    const badge = screen.getByLabelText('Confidence score: 30%')
    expect(badge).toHaveClass('bg-red-100', 'text-red-800')
  })

  it('handles edge cases correctly', () => {
    const { rerender } = render(<ConfidenceBadge score={0} />)
    expect(screen.getByText('0%')).toBeInTheDocument()
    
    rerender(<ConfidenceBadge score={1} />)
    expect(screen.getByText('100%')).toBeInTheDocument()
    
    rerender(<ConfidenceBadge score={0.5} />)
    expect(screen.getByText('50%')).toBeInTheDocument()
  })

  it('formats percentage correctly', () => {
    const { rerender } = render(<ConfidenceBadge score={0.8567} />)
    expect(screen.getByText('86%')).toBeInTheDocument()
    
    rerender(<ConfidenceBadge score={0.1234} />)
    expect(screen.getByText('12%')).toBeInTheDocument()
  })
})
