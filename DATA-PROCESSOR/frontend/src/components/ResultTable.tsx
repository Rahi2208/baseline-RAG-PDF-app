// ResultTable.tsx: shows ONE result table, sortable by clicking a column header
import { useMemo } from 'react'
import {
  createColumnHelper,
  createSortedRowModel,
  rowSortingFeature,
  sortFn_alphanumeric,
  sortFn_basic,
  tableFeatures,
  useTable,
} from '@tanstack/react-table'
import { ArrowUpDown } from 'lucide-react'
import type { Cell, ResultTable as ResultTableData } from '@/api/types'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'

type Row = Cell[]

// table features in use: only sorting. Kept outside the component so it isn't recreated on every render
const features = tableFeatures({
  rowSortingFeature,
  sortedRowModel: createSortedRowModel(),
  sortFns: { alphanumeric: sortFn_alphanumeric, basic: sortFn_basic },
})
const helper = createColumnHelper<typeof features, Row>()

export function ResultTable({ table }: { table: ResultTableData }) {
  // data from the backend is an array per row, so the i-th column is read with row[i]
  const columns = useMemo(
    () =>
      helper.columns(
        table.columns.map((name, i) => helper.accessor((row) => row[i], { id: String(i), header: name })),
      ),
    [table.columns],
  )

  const instance = useTable({ features, columns, data: table.rows })

  return (
    <Card>
      <CardHeader>
        <CardTitle>{table.title}</CardTitle>
        <CardDescription>{table.rows.length} {table.rows.length === 1 ? 'row' : 'rows'}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <Table>
          <TableHeader>
            {instance.getHeaderGroups().map((group) => (
              <TableRow key={group.id}>
                {group.headers.map((header) => (
                  <TableHead key={header.id}>
                    <button
                      className="inline-flex items-center gap-1 hover:text-foreground"
                      onClick={header.column.getToggleSortingHandler()}
                    >
                      <instance.FlexRender header={header} />
                      <ArrowUpDown className="size-3" />
                    </button>
                  </TableHead>
                ))}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {instance.getRowModel().rows.map((row) => (
              <TableRow key={row.id}>
                {row.getAllCells().map((cell) => (
                  <TableCell key={cell.id} className="tabular-nums">
                    {String(cell.getValue() ?? '')}
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>

        {/* formulas used: so the user can check the LLM didn't misread the guide */}
        <div className="rounded-md bg-muted p-3">
          <p className="mb-1 text-xs font-medium text-muted-foreground">Steps & formulas</p>
          <ul className="space-y-1 font-mono text-xs">
            {table.formulas.map((f, i) => (
              <li key={i}>{f}</li>
            ))}
          </ul>
        </div>
      </CardContent>
    </Card>
  )
}
