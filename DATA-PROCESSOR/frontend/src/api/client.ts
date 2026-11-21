// client.ts: all calls to the backend are collected here
import type { CreateJobResponse, JobStatus } from './types'

// backend address comes from the frontend .env (VITE_API_URL), default localhost:8000
export const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    // FastAPI sends errors as { detail: "..." }
    const body = await res.json().catch(() => null)
    throw new Error(body?.detail ?? `Request failed (${res.status})`)
  }
  return res.json() as Promise<T>
}

export async function createJob(files: File[]): Promise<CreateJobResponse> {
  const form = new FormData()
  files.forEach((f) => form.append('files', f)) // field name "files" = the parameter in FastAPI
  const res = await fetch(`${API_URL}/api/jobs`, { method: 'POST', body: form })
  return handle<CreateJobResponse>(res)
}

export async function getJobStatus(eventId: string): Promise<JobStatus> {
  const res = await fetch(`${API_URL}/api/jobs/${eventId}`)
  return handle<JobStatus>(res)
}

export function exportUrl(eventId: string): string {
  return `${API_URL}/api/jobs/${eventId}/export`
}
