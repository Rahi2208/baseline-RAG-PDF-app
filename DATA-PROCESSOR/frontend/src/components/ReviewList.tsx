// ReviewList.tsx: result of the "review" step, whether each instruction was followed or not
import { CircleCheck, CircleX } from 'lucide-react'
import type { CheckItem } from '@/api/types'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

export function ReviewList({ items }: { items: CheckItem[] }) {
  const done = items.filter((i) => i.done).length
  return (
    <Card>
      <CardHeader>
        <CardTitle>Instruction check</CardTitle>
        <CardDescription>
          {done}/{items.length} instructions followed
        </CardDescription>
      </CardHeader>
      <CardContent>
        <ul className="space-y-3">
          {items.map((item, i) => (
            <li key={i} className="flex gap-3">
              {item.done ? (
                <CircleCheck className="size-5 shrink-0 text-green-600" />
              ) : (
                <CircleX className="size-5 shrink-0 text-destructive" />
              )}
              <div>
                <p className="text-sm">{item.instruction}</p>
                <p className="text-xs text-muted-foreground">{item.note}</p>
              </div>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  )
}
