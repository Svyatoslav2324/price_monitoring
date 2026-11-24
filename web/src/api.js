const base = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '')
export const getMarketplaces = () => request('/imports/marketplaces')
export const SCHEDULES = { 60: 'Каждый час', 360: 'Раз в 6 часов', 1440: 'Раз в день' }
export const STATUSES = { active: 'Активен', paused: 'На паузе', error: 'Ошибка' }
export function priceLabel(product) {
  const amount = product.current_price?.toLocaleString('ru-RU', { maximumFractionDigits: 2 })
  switch (product.price_status) {
    case 'out_of_stock': return 'Нет в наличии'
    case 'unavailable_in_region': return 'Не доставляется в ваш регион'
    case 'not_found': return 'Карточка не найдена'
    case 'check_error': return amount == null ? 'Ошибка проверки' : `Ошибка проверки · последняя цена ${amount} ₽`
    default: return amount == null ? 'Ожидаем первую проверку' : `${amount} ₽`
  }
}

async function request(path, method = 'GET', body) {
  const headers = {}
  const token = localStorage.getItem('token')
  if (token) headers.Authorization = 'Bearer ' + token
  if (body && !(body instanceof URLSearchParams) && !(body instanceof FormData)) {
    headers['Content-Type'] = 'application/json'
    body = JSON.stringify(body)
  }
  const response = await fetch(base + path, { method, headers, body })
  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    if (response.status === 401 && token && !path.startsWith('/auth/')) {
      logout()
      window.location.reload()
    }
    throw new Error(typeof error.detail === 'string' ? error.detail : 'Ошибка запроса: ' + response.status)
  }
  if (response.status !== 204) return response.json()
}

export const getUser = () => localStorage.getItem('token') && localStorage.getItem('user')
export function logout() {
  localStorage.removeItem('token')
  localStorage.removeItem('user')
}
export async function authenticate(login, password, isRegister) {
  login = login.trim()
  if (isRegister) await request('/auth/register', 'POST', { login, password })
  const result = await request('/auth/login', 'POST', new URLSearchParams({ username: login, password }))
  localStorage.setItem('token', result.access_token)
  localStorage.setItem('user', login)
  return login
}

export async function addOrder({ url, schedule }) {
  return request('/imports/order', 'POST', { url, interval: Number(schedule) })
}

export async function getOrders() {
  const [subscriptions, markets] = await Promise.all([request('/subscriptions/'), getMarketplaces()])
  const rows = await Promise.all(subscriptions.map(async sub => {
    const group = await request('/groups/' + sub.group_id)
    return group.links.map(link => ({
      ...sub, schedule: sub.interval,
      product: { ...link, title: group.links.length === 1 ? group.title : link.url,
        marketplace: markets.find(mp => mp.id === link.marketplace_id)?.name || 'Маркетплейс' },
    }))
  }))
  return rows.flat()
}
export const deleteOrder = id => request('/subscriptions/' + id, 'DELETE')
export async function getProduct(id) {
  const row = (await getOrders()).find(order => String(order.product.id) === id)
  if (!row) throw new Error('Товар не найден')
  const history = await request('/links/' + id + '/history')
  return { product: { ...row.product, history } }
}

export const templateUrl = base + '/imports/template.xlsx'
export function importOrders(file) {
  const body = new FormData()
  body.append('file', file)
  return request('/imports/orders', 'POST', body)
}

export const getFolders = () => request('/folders')
export const createFolder = (marketplace_id, name) => request('/folders', 'POST', { marketplace_id, name })
export const moveProduct = (linkId, folder_id) => request('/folders/items/' + linkId, 'PUT', { folder_id })
