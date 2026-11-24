import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { getOrders, getMarketplaces, getFolders, createFolder, moveProduct, deleteOrder, priceLabel, SCHEDULES, STATUSES } from '../api'


export default function Orders() {
  const [orders, setOrders] = useState(null) // null = ещё грузится
  const [confirmId, setConfirmId] = useState(null) // id заказа, который собираются удалить
  const navigate = useNavigate()

  const [error, setError] = useState('')
  const [markets, setMarkets] = useState([])
  const [library, setLibrary] = useState({ folders: [], items: {} })
  const [editingMarket, setEditingMarket] = useState(null)
  const [name, setName] = useState('')
  const [busy, setBusy] = useState(false)
  const load = () => Promise.all([getOrders(), getFolders(), getMarketplaces()]).then(([rows, groups, catalog]) => {
    setMarkets(catalog)
    setOrders(rows)
    setLibrary(groups)
  }).catch(err => setError(err.message))
  async function change(action) {
    setBusy(true)
    setError('')
    try {
      await action()
      const updated = await getFolders()
      setLibrary(updated)
    } catch (err) { setError(err.message) }
    finally { setBusy(false) }
  }
  useEffect(() => { load() }, [])

  const handleDelete = async id => {
    try {
      await deleteOrder(id)
      setConfirmId(null)
      await load()
    } catch (err) { setError(err.message) }
  }
  if (error && orders === null) return <main role="alert">{error}</main>
  if (orders === null) return <main><p className="sub">Загрузка…</p></main>

  return (
    <main>
      <div className="row">
        <div style={{ marginRight: 'auto' }}>
          <h1>Мои отслеживания</h1>
          <p className="sub" style={{ margin: 0 }}>Отслеживаемых товаров: {orders.length}</p>
        </div>
        <button className="btn pri" onClick={() => navigate('/add')}>Добавить товар</button>
      </div>

      {error && <p className="err" role="alert">{error}</p>}
      {!orders.length && !library.folders.length && <div className="card empty">Вы пока ничего не отслеживаете.</div>}
      {Array.from(new Set([...orders.map(o => o.product.marketplace_id), ...library.folders.map(f => f.marketplace_id)])).map(marketId => {
        const rows = orders.filter(o => o.product.marketplace_id === marketId)
        const folders = library.folders.filter(f => f.marketplace_id === marketId)
        const market = rows[0]?.product.marketplace || markets.find(m => m.id === marketId)?.name || 'Маркетплейс'
        return <section className="market-section" key={marketId}>
          <div className="market-heading">
            <h2>{market} <small>{rows.length}</small></h2>
            <button className="btn" onClick={() => { setEditingMarket(marketId); setName('') }}>Создать группу</button>
          </div>
          {editingMarket === marketId && <form className="folder-form" onSubmit={e => {
            e.preventDefault()
            change(async () => {
              await createFolder(marketId, name.trim())
              setEditingMarket(null)
            })
          }}>
            <input autoFocus aria-label="Название группы" placeholder="Название группы" maxLength={80} value={name} onChange={e => setName(e.target.value)} />
            <button className="btn pri" disabled={busy || !name.trim()}>Создать</button>
            <button type="button" className="btn" onClick={() => setEditingMarket(null)}>Отмена</button>
          </form>}
          {[...folders, { id: null, name: 'Без группы' }].map(folder => {
            const members = rows.filter(o => (library.items[o.product.id] ?? null) === folder.id)
            if (!folder.id && !members.length) return null
            return <details key={folder.id ?? 'none'} className="folder-box">
              <summary>{folder.name} <small>{members.length}</small></summary>
              {!members.length ? <p className="sub">Выберите эту группу в строке товара.</p> : <div className="scroll">
          <table>
            <thead>
              <tr>
                <th>Товар</th><th>Группа</th>
                <th className="num">Сейчас</th>
                <th>Статус</th><th>Проверка</th><th></th>
              </tr>
            </thead>
            <tbody>
              {members.map((o) => (
                <tr key={o.id + "-" + o.product.id}>
                  <td><Link className="lk" to={`/product/${o.product.id}`}>{o.product.title}</Link></td>
                  <td><select aria-label="Группа товара" value={folder.id ?? ''} disabled={busy}
                    onChange={e => { const id = Number(e.target.value) || null; change(() => moveProduct(o.product.id, id)) }}>
                    <option value="">Без группы</option>
                    {folders.map(f => <option value={f.id} key={f.id}>{f.name}</option>)}
                  </select></td>
                  <td className="num">{priceLabel(o.product)}</td>
                  <td><span className={'b ' + o.status}>{STATUSES[o.status] || o.status}</span></td>
                  <td>{SCHEDULES[o.schedule] || o.schedule + ' мин'}</td>
                  <td>
                    <div className="acts">
                      {confirmId === o.id ? (
                        <>
                          <button className="btn dng" onClick={() => handleDelete(o.id)}>Да, отписаться от группы</button>
                          <button className="btn" onClick={() => setConfirmId(null)}>Отмена</button>
                        </>
                      ) : (
                        <button className="btn dng" onClick={() => setConfirmId(o.id)}>Отписаться</button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table></div>}
            </details>
          })}
        </section>
      })}
    </main>
  )
}
