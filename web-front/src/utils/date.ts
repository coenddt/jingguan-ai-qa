import dayjs from 'dayjs'

/** 格式化日期为 YYYY-MM-DD HH:mm，空/无效返回 '-' */
export function formatDateTime(value: string | number | Date | null | undefined): string {
  if (!value) return '-'
  const d = dayjs(value)
  return d.isValid() ? d.format('YYYY-MM-DD HH:mm') : '-'
}
