export default function ScoreBar({ value, max = 10 }: { value: number; max?: number }) {
  const pct = Math.max(0, Math.min(100, (value / max) * 100))
  const tone = value >= 8 ? 'high' : value >= 5 ? 'mid' : 'low'
  return (
    <div className="scorebar">
      <div className="scorebar-track">
        <div className={`scorebar-fill ${tone}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="scorebar-num">{value.toFixed(1)}</span>
    </div>
  )
}
