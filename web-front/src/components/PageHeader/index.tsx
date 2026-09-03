import PageTitle from '../PageTitle'
import Breadcrumb from '../Breadcrumb'
import type { PageAction } from '../PageTitle'

/** 布局层页头 = 面包屑 + 标题区（复用 PageTitle/Breadcrumb） */
export default function PageHeader(props: {
  title: string
  subtitle?: string
  onRefresh?: () => void
  actions?: PageAction[]
}) {
  return (
    <div className="mb-5">
      <Breadcrumb />
      <PageTitle {...props} />
    </div>
  )
}
