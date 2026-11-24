import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getProduct, priceLabel } from '../api'
import PriceChart from '../components/PriceChart'

const rub = (n) => n.toLocaleString('ru-RU') + ' ₽'

export default function Product() {
  const { id } = useParams()
  const [data, setData] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    getProduct(id).then(setData).catch((e) => setError(e.message))
  }, [id])

  if (error) return <main><p className="err">{error}</p><Link className="btn" to="/orders">Назад к списку</Link></main>
  if (!data) return <main><p className="sub">Загрузка…</p></main>

  const { product } = data
  const prices = product.history.map((h) => h.price)
  return (
    <main>
      <div className="row"><Link className="btn" to="/orders">Назад к списку</Link></div>
      <h1>{product.title}</h1>
      <p className="sub">
        {product.marketplace} ·{' '}
        <a href={product.url} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--ac)' }}>Открыть товар на маркетплейсе</a>
      </p>

      <div className="stats">
        <div className="st"><small>Сейчас</small><b>{priceLabel(product)}</b></div>
        <div className="st"><small>Минимум по истории</small><b>{prices.length ? rub(Math.min(...prices)) : '—'}</b></div>
        <div className="st"><small>Максимум по истории</small><b>{prices.length ? rub(Math.max(...prices)) : '—'}</b></div>
      </div>

      <div className="card">
        <h2 style={{ fontSize: 16, margin: '0 0 12px' }}>История цены</h2>
        {prices.length ? <PriceChart history={product.history} /> : <p>Пока нет замеров цены.</p>}
      </div>
    </main>
  )
}
