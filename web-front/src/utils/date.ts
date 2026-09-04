import dayjs from 'dayjs'

/** 格式化日期为 YYYY-MM-DD HH:mm，空/无效返回 '-' */
export function formatDateTime(value: string | number | Date | null | undefined): string {
  if (!value) return '-'
  const d = dayjs(value)
  return d.isValid() ? d.format('YYYY-MM-DD HH:mm') : '-'
}

/** 格式化时间为 HH:mm:ss（日志步骤时间戳用），空/无效返回 '-' */
export function formatClock(value: string | number | Date | null | undefined): string {
  if (!value) return '-'
  const d = dayjs(value)
  return d.isValid() ? d.format('HH:mm:ss') : '-'
}
