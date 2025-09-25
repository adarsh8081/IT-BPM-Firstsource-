/**
 * @jest-environment jsdom
 */

import React from 'react'
import { render, screen } from '@testing-library/react'
import PrivacyMask from '@/components/ui/PrivacyMask'

describe('PrivacyMask', () => {
  it('masks phone number for non-privileged user', () => {
    const { container } = render(
      <PrivacyMask data="+1-555-123-4567" type="phone" />
    )
    expect(container.firstChild).toMatchSnapshot()
    
    expect(screen.getByLabelText('Masked phone')).toBeInTheDocument()
    expect(screen.getByText('***-***-4567')).toBeInTheDocument()
  })

  it('shows full phone number for privileged user', () => {
    const { container } = render(
      <PrivacyMask data="+1-555-123-4567" type="phone" isPrivileged={true} />
    )
    expect(container.firstChild).toMatchSnapshot()
    
    expect(screen.getByLabelText('Masked phone')).toBeInTheDocument()
    expect(screen.getByText('+1-555-123-4567')).toBeInTheDocument()
  })

  it('masks email for non-privileged user', () => {
    const { container } = render(
      <PrivacyMask data="john.smith@example.com" type="email" />
    )
    expect(container.firstChild).toMatchSnapshot()
    
    expect(screen.getByLabelText('Masked email')).toBeInTheDocument()
    expect(screen.getByText('j***@example.com')).toBeInTheDocument()
  })

  it('shows full email for privileged user', () => {
    const { container } = render(
      <PrivacyMask data="john.smith@example.com" type="email" isPrivileged={true} />
    )
    expect(container.firstChild).toMatchSnapshot()
    
    expect(screen.getByLabelText('Masked email')).toBeInTheDocument()
    expect(screen.getByText('john.smith@example.com')).toBeInTheDocument()
  })

  it('masks SSN for non-privileged user', () => {
    const { container } = render(
      <PrivacyMask data="123-45-6789" type="ssn" />
    )
    expect(container.firstChild).toMatchSnapshot()
    
    expect(screen.getByLabelText('Masked ssn')).toBeInTheDocument()
    expect(screen.getByText('***-**-****')).toBeInTheDocument()
  })

  it('shows full SSN for privileged user', () => {
    const { container } = render(
      <PrivacyMask data="123-45-6789" type="ssn" isPrivileged={true} />
    )
    expect(container.firstChild).toMatchSnapshot()
    
    expect(screen.getByLabelText('Masked ssn')).toBeInTheDocument()
    expect(screen.getByText('123-45-6789')).toBeInTheDocument()
  })

  it('masks default type for non-privileged user', () => {
    const { container } = render(
      <PrivacyMask data="sensitive-data" type="default" />
    )
    expect(container.firstChild).toMatchSnapshot()
    
    expect(screen.getByLabelText('Masked default')).toBeInTheDocument()
    expect(screen.getByText('********')).toBeInTheDocument()
  })

  it('handles empty data gracefully', () => {
    render(<PrivacyMask data="" type="phone" />)
    
    expect(screen.getByLabelText('Masked phone')).toBeInTheDocument()
    expect(screen.getByText('')).toBeInTheDocument()
  })

  it('handles short phone numbers', () => {
    render(<PrivacyMask data="123" type="phone" />)
    
    expect(screen.getByLabelText('Masked phone')).toBeInTheDocument()
    expect(screen.getByText('123')).toBeInTheDocument()
  })

  it('handles malformed email addresses', () => {
    render(<PrivacyMask data="invalid-email" type="email" />)
    
    expect(screen.getByLabelText('Masked email')).toBeInTheDocument()
    expect(screen.getByText('***')).toBeInTheDocument()
  })

  it('handles null data', () => {
    render(<PrivacyMask data={null as any} type="phone" />)
    
    expect(screen.getByLabelText('Masked phone')).toBeInTheDocument()
    expect(screen.getByText('')).toBeInTheDocument()
  })

  it('handles undefined data', () => {
    render(<PrivacyMask data={undefined as any} type="phone" />)
    
    expect(screen.getByLabelText('Masked phone')).toBeInTheDocument()
    expect(screen.getByText('')).toBeInTheDocument()
  })

  it('memoizes masked data correctly', () => {
    const { rerender } = render(
      <PrivacyMask data="+1-555-123-4567" type="phone" />
    )
    
    expect(screen.getByText('***-***-4567')).toBeInTheDocument()
    
    // Re-render with same props
    rerender(<PrivacyMask data="+1-555-123-4567" type="phone" />)
    expect(screen.getByText('***-***-4567')).toBeInTheDocument()
    
    // Re-render with different privilege
    rerender(<PrivacyMask data="+1-555-123-4567" type="phone" isPrivileged={true} />)
    expect(screen.getByText('+1-555-123-4567')).toBeInTheDocument()
  })
})
