import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'

describe('configuración de pruebas', () => {
  it('dibuja un componente y lo encuentra en pantalla', () => {
    render(<p>Hola PAMI</p>)
    expect(screen.getByText('Hola PAMI')).toBeInTheDocument()
  })
})