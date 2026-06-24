export const STATUS_LABEL: Record<string, string> = {
  pending: '대기 중',
  ingesting: '코드 수집 중',
  judging: 'AI 심사 중',
  scored: '심사 완료',
  failed: '실패',
}

export function isInProgress(status: string): boolean {
  return status === 'pending' || status === 'ingesting' || status === 'judging'
}

export const STAGE_LABEL: Record<string, string> = {
  interim: '중간',
  final: '최종',
}

export function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString('ko-KR')
  } catch {
    return iso
  }
}
