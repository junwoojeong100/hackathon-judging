import { STAGE_LABEL } from '../status'

export default function StageBadge({ stage }: { stage: string }) {
  return <span className={`stage stage-${stage}`}>{STAGE_LABEL[stage] || stage}</span>
}
