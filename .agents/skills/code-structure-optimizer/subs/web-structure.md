# Web 开发结构规范（页面即布局盒）

Web 开发（web-saas）遵循"页面即布局盒"原则：业务逻辑下沉到组件与 hooks，页面只负责编排。新建页面、组件、功能模块时，按本节粒度强制拆分。

**页面职责**
- 页面不含具体业务逻辑，仅作为布局各模块的盒子
- 页面只做三件事：路由参数解析、模块编排（组合组件）、顶层状态协调
- 页面禁内联：数据转换、复杂条件判断、业务计算——一律下沉到组件或 hooks

```jsx
// ❌ 反例：页面塞满业务逻辑
function AuctionListPage() {
  const [items, setItems] = useState([])
  const [filters, setFilters] = useState({})
  useEffect(() => { fetchItems(filters).then(setItems) }, [filters])
  const handleRecalc = async (id) => { /* 30 行重算逻辑 */ }
  const handlePublish = async (id) => { /* 20 行发布逻辑 */ }
  return (
    <div>
      <FilterArea onChange={setFilters} />
      <Table data={items} columns={[
        { field: 'title', render: (row) => <span>{row.title}{row.urgent && '⚠'}</span> },
        { field: 'actions', render: (row) => (
          <>
            <Button onClick={() => handleRecalc(row.id)}>重算</Button>
            <Button onClick={() => handlePublish(row.id)}>发布</Button>
          </>
        )},
      ]} />
    </div>
  )
}

// ✅ 正例：页面只编排，逻辑下沉
function AuctionListPage() {
  const { items, filters, setFilters } = useAuctionList()      // hooks
  return (
    <div>
      <FilterArea value={filters} onChange={setFilters} />     // 组件
      <AuctionTable items={items} />                           // 组件
    </div>
  )
}
```

**组件封装粒度**
- 页面内所有元素都封装为独立组件，不在页面内写内联 JSX 块
- 表格操作按钮：**每个按钮单独封装一个组件**（含点击逻辑、二次确认、loading 状态、权限控制）
- 表格自定义单元格：**凡需自定义渲染的单元格，每个单独封装一个组件**（状态标签、用户卡片、金额、附件缩略图等）
- 组件通过 props 接收数据与回调，不直接耦合页面状态

```jsx
// 表格列定义：每按钮一组件，每自定义单元格一组件
const columns = [
  { field: 'status', render: (row) => <BugStatusCell row={row} /> },        // 单元格组件
  { field: 'assignee', render: (row) => <UserDisplayCard user={row.assignee} /> },
  { field: 'amount', render: (row) => <AmountCell value={row.amount} /> },
  { field: 'actions', render: (row) => (
      <ActionCell>
        <RecalcScoreButton item={row} />          // 操作按钮组件
        <PublishButton item={row} />
        <DeleteButton item={row} />
      </ActionCell>
    )},
]

// 单个操作按钮组件：自带二次确认 + loading + 权限
function RecalcScoreButton({ item }) {
  const [loading, setLoading] = useState(false)
  const { confirm } = useConfirm()
  const handleClick = async () => {
    if (!await confirm(`确认重算「${item.title}」的精选分？`)) return
    setLoading(true)
    try { await recalcScore(item._id) } finally { setLoading(false) }
  }
  return <Button onClick={handleClick} loading={loading}>重算</Button>
}
```

**Hooks 抽象**
- 凡可用于多页面共用的通用逻辑，都封装为自定义 hooks
- hooks 命名以 `use` 开头，返回状态与操作方法
- 单一职责：一个 hook 只管一个领域（如 `useTableData` / `useTableFilters` / `useExport` / `useSnackbar`）

```js
// 跨页面共用：列表数据 + 筛选 + 分页
function useAuctionList() {
  const [items, setItems] = useState([])
  const [filters, setFilters] = useState({})
  const [page, setPage] = useState(1)
  useEffect(() => { fetchItems(filters, page).then(setItems) }, [filters, page])
  return { items, filters, setFilters, page, setPage }
}
```

**目录组织**
```
features/auction/
  pages/AuctionListPage.jsx              — 页面（仅编排）
  components/                            — 页面内组件
    AuctionTable/
    FilterArea/
    cells/BugStatusCell.jsx              — 自定义单元格
    cells/UserDisplayCard.jsx
    buttons/RecalcScoreButton.jsx        — 操作按钮
    buttons/PublishButton.jsx
  hooks/useAuctionList.js                — 页面专用 hooks
shared/hooks/useSnackbar.js              — 跨页面通用 hooks
```
