const API_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '')
const TOKEN_KEY = 'judith_owner_token'
const getToken = () => window.localStorage.getItem(TOKEN_KEY)

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
  const token = getToken()
  const response = await fetch(`${API_URL}${path}`, { ...options, headers:{'Content-Type':'application/json', ...(token && path !== '/api/auth/login' ? { Authorization: `Bearer ${token}` } : {}), ...(options?.headers || {})} })
  const body = await response.json().catch(() => ({}))
  if (!response.ok) {
    if (response.status === 401 && path !== '/api/auth/login') {
      window.localStorage.removeItem(TOKEN_KEY)
      window.dispatchEvent(new Event('judith-auth-expired'))
    }
    throw new ApiError(response.status, body.detail, `Request failed (${response.status})`)
  }
  return body
}

export const api = {
  login: async (username:string,password:string) => {
    const result = await request<{access_token:string}>('/api/auth/login',{method:'POST',body:JSON.stringify({username,password})})
    window.localStorage.setItem(TOKEN_KEY,result.access_token)
    return result
  },
  logout: () => window.localStorage.removeItem(TOKEN_KEY),
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
