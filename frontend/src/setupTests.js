import '@testing-library/jest-dom/vitest'
import { afterEach } from 'vitest'
import { cleanup } from '@testing-library/react'

// Limpia lo que se dibujó en pantalla después de cada prueba
afterEach(() => {
  cleanup()
})