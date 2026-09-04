const API_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '')

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {headers:{'Content-Type':'application/json', ...(options?.headers || {})}, ...options})
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new Error(body.detail || `Request failed (${response.status})`)
  }
  return response.json()
}

export const api = {
  styles: () => request<any[]>('/api/styles'),
  availability: (date: string, start: string, end: string) => request<any>(`/api/availability?date=${date}&start_time=${start}&end_time=${end}`),
  dashboard: () => request<any>('/api/dashboard'),
  appointments: () => request<any[]>('/api/appointments'),
  createAppointment: (payload: unknown) => request<any>('/api/appointments', {method:'POST', body:JSON.stringify(payload)}),
  start: (id: string) => request<any>(`/api/appointments/${id}/start`, {method:'POST'}),
  complete: (id: string) => request<any>(`/api/appointments/${id}/complete`, {method:'POST'}),
  cancel: (id: string) => request<any>(`/api/appointments/${id}/cancel`, {method:'POST'}),
}
