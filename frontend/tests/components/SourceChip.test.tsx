/**
 * @jest-environment jsdom
 */

import React from 'react'
import { render, screen } from '@testing-library/react'
import SourceChip from '@/components/ui/SourceChip'

describe('SourceChip', () => {
  it('renders NPI source correctly', () => {
    const { container } = render(<SourceChip source="npi" />)
    expect(container.firstChild).toMatchSnapshot()
    
    expect(screen.getByLabelText('Data source: npi')).toBeInTheDocument()
    expect(screen.getByText('Npi')).toBeInTheDocument()
  })

  it('renders Google Places source correctly', () => {
    const { container } = render(<SourceChip source="google_places" />)
    expect(container.firstChild).toMatchSnapshot()
    
    expect(screen.getByLabelText('Data source: google_places')).toBeInTheDocument()
    expect(screen.getByText('Google Places')).toBeInTheDocument()
  })

  it('renders State Board source correctly', () => {
    const { container } = render(<SourceChip source="state_board" />)
    expect(container.firstChild).toMatchSnapshot()
    
    expect(screen.getByLabelText('Data source: state_board')).toBeInTheDocument()
    expect(screen.getByText('State Board')).toBeInTheDocument()
  })

  it('renders Hospital Website source correctly', () => {
    const { container } = render(<SourceChip source="hospital_website" />)
    expect(container.firstChild).toMatchSnapshot()
    
    expect(screen.getByLabelText('Data source: hospital_website')).toBeInTheDocument()
    expect(screen.getByText('Hospital Website')).toBeInTheDocument()
  })

  it('renders OCR source correctly', () => {
    const { container } = render(<SourceChip source="ocr" />)
    expect(container.firstChild).toMatchSnapshot()
    
    expect(screen.getByLabelText('Data source: ocr')).toBeInTheDocument()
    expect(screen.getByText('Ocr')).toBeInTheDocument()
  })

  it('renders Internal source correctly', () => {
    const { container } = render(<SourceChip source="internal" />)
    expect(container.firstChild).toMatchSnapshot()
    
    expect(screen.getByLabelText('Data source: internal')).toBeInTheDocument()
    expect(screen.getByText('Internal')).toBeInTheDocument()
  })

  it('renders unknown source with default styling', () => {
    const { container } = render(<SourceChip source="unknown_source" />)
    expect(container.firstChild).toMatchSnapshot()
    
    expect(screen.getByLabelText('Data source: unknown_source')).toBeInTheDocument()
    expect(screen.getByText('Unknown Source')).toBeInTheDocument()
  })

  it('applies correct variant classes for NPI source', () => {
    render(<SourceChip source="npi" />)
    
    const chip = screen.getByLabelText('Data source: npi')
    expect(chip).toHaveClass('border-blue-200', 'bg-blue-50', 'text-blue-700')
  })

  it('applies correct variant classes for Google Places source', () => {
    render(<SourceChip source="google_places" />)
    
    const chip = screen.getByLabelText('Data source: google_places')
    expect(chip).toHaveClass('border-green-200', 'bg-green-50', 'text-green-700')
  })

  it('applies correct variant classes for State Board source', () => {
    render(<SourceChip source="state_board" />)
    
    const chip = screen.getByLabelText('Data source: state_board')
    expect(chip).toHaveClass('border-red-200', 'bg-red-50', 'text-red-700')
  })

  it('renders with custom className', () => {
    const { container } = render(
      <SourceChip source="npi" className="custom-class" />
    )
    expect(container.firstChild).toMatchSnapshot()
    
    const chip = screen.getByLabelText('Data source: npi')
    expect(chip).toHaveClass('custom-class')
  })

  it('formats source names correctly', () => {
    const { rerender } = render(<SourceChip source="google_places" />)
    expect(screen.getByText('Google Places')).toBeInTheDocument()
    
    rerender(<SourceChip source="state_board" />)
    expect(screen.getByText('State Board')).toBeInTheDocument()
    
    rerender(<SourceChip source="hospital_website" />)
    expect(screen.getByText('Hospital Website')).toBeInTheDocument()
  })

  it('handles empty source gracefully', () => {
    render(<SourceChip source="" />)
    
    expect(screen.getByLabelText('Data source: ')).toBeInTheDocument()
    expect(screen.getByText('')).toBeInTheDocument()
  })
})
