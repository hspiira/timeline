/**
 * Client entry.
 *
 * The app renders entirely in the browser: every route but the landing and
 * verification pages sits behind a login, so server rendering bought nothing and
 * cost a second runtime beside the API. Public pages are served by the API itself.
 */
import { RouterProvider } from '@tanstack/react-router'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import { getRouter } from './router'
import './styles.css'

const router = getRouter()

const rootElement = document.getElementById('root')
if (!rootElement) {
  throw new Error('Root element #root is missing from index.html')
}

createRoot(rootElement).render(
  <StrictMode>
    <RouterProvider router={router} />
  </StrictMode>,
)
