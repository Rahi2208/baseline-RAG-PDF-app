// files.ts: guess the file type from its extension (same as classify() in the backend)
export type FileKind = 'guide' | 'data'

const GUIDE_EXT = ['.pdf', '.png', '.jpg', '.jpeg', '.webp']
const DATA_EXT = ['.xlsx', '.csv']

export function fileKind(name: string): FileKind | null {
  const ext = name.slice(name.lastIndexOf('.')).toLowerCase()
  if (GUIDE_EXT.includes(ext)) return 'guide'
  if (DATA_EXT.includes(ext)) return 'data'
  return null
}

// return a message if the file combination is incomplete, null if it's fine
export function validateFiles(files: File[]): string | null {
  const guides = files.filter((f) => fileKind(f.name) === 'guide').length
  const datas = files.filter((f) => fileKind(f.name) === 'data').length
  if (guides === 0) return 'Add at least 1 guide file (PDF/image)'
  if (datas !== 1) return 'Need exactly 1 data file (.xlsx/.csv)'
  return null
}
