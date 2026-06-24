import { STATUS_LABEL } from '../status'

export default function StatusBadge({ status }: { status: string }) {
  return <span className={`badge badge-${status}`}>{STATUS_LABEL[status] || status}</span>
}
