// types.ts: the "twin" of custom_types.py in the backend
// if the data shape changes in the backend, change it here too

export type Cell = string | number | boolean | null

export interface ResultTable {
  id: string
  title: string
  columns: string[]
  rows: Cell[][]
  formulas: string[]
}

export interface CheckItem {
  instruction: string
  done: boolean
  note: string
}

export interface JobResult {
  instructions: { items: string[]; expected_tables: string[] }
  tables: ResultTable[]
  review: { items: CheckItem[] }
}

export interface JobStatus {
  status: 'running' | 'completed' | 'failed'
  result: JobResult | null
  error: string | null
}

export interface CreateJobResponse {
  job_id: string
  event_id: string
}
