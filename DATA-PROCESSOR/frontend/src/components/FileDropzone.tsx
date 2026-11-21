// FileDropzone.tsx: drag & drop area + list of the files already chosen
import { FileSpreadsheet, FileText, Upload, X } from 'lucide-react'
import { useDropzone } from 'react-dropzone'
import { fileKind } from '@/api/files'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

interface Props {
  files: File[]
  onChange: (files: File[]) => void
  disabled?: boolean
}

export function FileDropzone({ files, onChange, disabled }: Props) {
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    disabled,
    accept: {
      'application/pdf': ['.pdf'],
      'image/*': ['.png', '.jpg', '.jpeg', '.webp'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'text/csv': ['.csv'],
    },
    // new files are added to the list (not replacing it)
    onDrop: (accepted) => onChange([...files, ...accepted]),
  })

  const remove = (index: number) => onChange(files.filter((_, i) => i !== index))

  return (
    <div className="space-y-3">
      <div
        {...getRootProps()}
        className={cn(
          'flex cursor-pointer flex-col items-center gap-2 rounded-lg border-2 border-dashed p-8 text-center transition-colors',
          isDragActive ? 'border-primary bg-muted' : 'hover:bg-muted/50',
          disabled && 'cursor-not-allowed opacity-50',
        )}
      >
        <input {...getInputProps()} />
        <Upload className="size-8 text-muted-foreground" />
        <p className="font-medium">
          {isDragActive ? 'Drop files here…' : 'Drag & drop files, or click to choose'}
        </p>
        <p className="text-sm text-muted-foreground">
          Guide: PDF / image · Data: 1 .xlsx / .csv file
        </p>
      </div>

      {files.length > 0 && (
        <ul className="space-y-2">
          {files.map((file, i) => {
            const kind = fileKind(file.name)
            const Icon = kind === 'data' ? FileSpreadsheet : FileText
            return (
              <li key={`${file.name}-${i}`} className="flex items-center gap-3 rounded-md border px-3 py-2">
                <Icon className="size-4 shrink-0 text-muted-foreground" />
                <span className="flex-1 truncate text-sm">{file.name}</span>
                <Badge variant={kind === 'data' ? 'default' : 'secondary'}>{kind ?? '?'}</Badge>
                <Button variant="ghost" size="icon" onClick={() => remove(i)} disabled={disabled}
                        aria-label={`Remove ${file.name}`}>
                  <X />
                </Button>
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}
