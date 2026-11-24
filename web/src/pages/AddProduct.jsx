import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { addOrder, importOrders, templateUrl, getMarketplaces, SCHEDULES } from '../api'

export default function AddProduct() {
  const [url, setUrl] = useState('')
  const [schedule, setSchedule] = useState('60')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [file, setFile] = useState(null)
  const [report, setReport] = useState('')
  const [markets, setMarkets] = useState([])
  useEffect(() => { getMarketplaces().then(setMarkets).catch(err => setError(err.message)) }, [])
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      await addOrder({ url: url.trim(), schedule })
      navigate('/orders')
    } catch (err) {
      setError(err.message)
      setBusy(false)
    }
  }

  async function upload(e) {
    e.preventDefault()
    setBusy(true)
    setReport('')
    try {
      await importOrders(file)
      navigate('/orders')
    } catch (err) {
      setReport(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <main>
      <h1>Добавить товар</h1>
      <p className="sub">Вставьте ссылку на товар.</p>
      <div className="card" style={{ maxWidth: 560 }}>
        <form onSubmit={handleSubmit}>
          <div className="f">
            <label htmlFor="url">Ссылка на товар</label>
            <input required maxLength={255} type="url" id="url" value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://www.ozon.ru/product/…" />
            {markets.length > 0 && <div className="hint">Принимаем ссылки: {markets.map(m => m.name).join(', ')}</div>}
          </div>
          <div className="f">
            <label htmlFor="schedule">Как часто проверять цену</label>
            <select id="schedule" value={schedule} onChange={(e) => setSchedule(e.target.value)}>
              {Object.entries(SCHEDULES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
          </div>
          <p className="err" role="alert">{error}</p>
          <button disabled={busy} className="btn pri">Начать отслеживание</button>
        </form>
      </div>
      <section className="card" style={{ maxWidth: 560 }}>
        <h2>Загрузить ссылки из Excel</h2>
        <p><a className="lk" href={templateUrl} download>Скачать шаблон Excel</a></p>
        <p>Вставьте по одной ссылке на карточку товара в каждую строку. Интервал — 60, 360 или 1440 минут. Пустая ячейка означает 60 минут.</p>
        <form onSubmit={upload}>
          <label htmlFor="orders-file">Файл .xlsx, до 500 ссылок и 512 КБ</label>
          <input required id="orders-file" type="file" accept=".xlsx" onChange={e => {
            setFile(e.target.files[0])
            setReport('')
          }} />
          <button className="btn pri" disabled={busy || !file}>Добавить из файла</button>
          <p role="status">{report}</p>
        </form>
      </section>
    </main>
  )
}
