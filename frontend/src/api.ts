const API_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '')

export class ApiError extends Error {
  status: number
  detail: any
  constructor(status: number, detail: any, fallback: string) {
    const message = typeof detail === 'string' ? detail : detail?.message || fallback
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {headers:{'Content-Type':'application/json', ...(options?.headers || {})}, ...options})
  const body = await response.json().catch(() => ({}))
  if (!response.ok) throw new ApiError(response.status, body.detail, `Request failed (${response.status})`)
  return body
}

export const api = {
  styles: () => request<any[]>('/api/styles'),
  availability: (date:string,start:string,end:string) => request<any>(`/api/availability?date=${encodeURIComponent(date)}&start_time=${encodeURIComponent(start)}&end_time=${encodeURIComponent(end)}`),
  dashboard: () => request<any>('/api/dashboard'),
  appointments: () => request<any[]>('/api/appointments'),
  createAppointment: (payload:unknown) => request<any>('/api/appointments',{method:'POST',body:JSON.stringify(payload)}),
  updateAppointment: (id:string,payload:unknown) => request<any>(`/api/appointments/${id}`,{method:'PATCH',body:JSON.stringify(payload)}),
  start: (id:string) => request<any>(`/api/appointments/${id}/start`,{method:'POST'}),
  complete: (id:string) => request<any>(`/api/appointments/${id}/complete`,{method:'POST'}),
  cancel: (id:string) => request<any>(`/api/appointments/${id}/cancel`,{method:'POST'}),
  noShow: (id:string) => request<any>(`/api/appointments/${id}/no-show`,{method:'POST'}),
  payment: (id:string,payload:unknown) => request<any>(`/api/appointments/${id}/payments`,{method:'POST',body:JSON.stringify(payload)}),
  paymentHistory: (id:string) => request<any[]>(`/api/appointments/${id}/payments`),
  customers: (q='') => request<any[]>(`/api/customers${q?`?q=${encodeURIComponent(q)}`:''}`),
  customer: (id:string) => request<any>(`/api/customers/${id}`),
  updateCustomer: (id:string,payload:unknown) => request<any>(`/api/customers/${id}`,{method:'PATCH',body:JSON.stringify(payload)}),
  blockedTimes: () => request<any[]>('/api/blocked-times'),
  createBlockedTime: (payload:unknown) => request<any>('/api/blocked-times',{method:'POST',body:JSON.stringify(payload)}),
  deleteBlockedTime: (id:string) => request<any>(`/api/blocked-times/${id}`,{method:'DELETE'}),
}
