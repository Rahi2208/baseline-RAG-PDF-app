// useJob.ts: submit a job + watch its status until it finishes
import { useMutation, useQuery } from '@tanstack/react-query'
import { createJob, getJobStatus } from '@/api/client'

const POLL_MS = 1500 // check status every 1.5 seconds

export function useJob() {
  // useMutation = for actions that "change something" (uploading files)
  const upload = useMutation({ mutationFn: createJob })
  const eventId = upload.data?.event_id

  // useQuery = for "fetching data"; refetchInterval makes it keep asking again
  const status = useQuery({
    queryKey: ['job', eventId],
    queryFn: () => getJobStatus(eventId!),
    enabled: Boolean(eventId), // only runs after the upload succeeds
    refetchInterval: (query) => {
      const s = query.state.data?.status
      return s === 'completed' || s === 'failed' ? false : POLL_MS // stop once it's finished
    },
  })

  const isRunning =
    upload.isPending || (Boolean(eventId) && (!status.data || status.data.status === 'running'))

  return {
    start: upload.mutate,
    reset: upload.reset,
    eventId,
    isRunning,
    uploadError: upload.error,
    job: status.data,
    pollError: status.error,
  }
}
