import { expect, Page, test } from '@playwright/test'

// Критерии приёмки ТЗ, раздел 9 (модель 09_09_26). Логин/пароль — из окружения.
const LOGIN = process.env.E2E_LOGIN ?? 'admin'
const PASSWORD = process.env.E2E_PASSWORD ?? ''

async function openDashboard(page: Page) {
  await page.clock.setFixedTime(new Date('2026-09-29T12:00:00+03:00'))
  await page.goto('/')
  await page.getByLabel('Логин').fill(LOGIN)
  await page.getByLabel('Пароль').fill(PASSWORD)
  await page.getByRole('button', { name: 'Войти' }).click()
  await page.getByRole('button', { name: /Сокольники 09 09 new FM/ }).click()
  await expect(page.getByTestId('price-val')).not.toHaveText('—')
  // сбросить сценарий, сохранённый прошлым прогоном
  await page.getByRole('button', { name: 'Сбросить' }).click()
  await page.getByRole('button', { name: '1', exact: true }).click()
}

const oursLabels = (page: Page, kind: 'price' | 'pace') => page.locator(`svg[data-chart="${kind}"] text.ours-label`)

test('открытие дашборда: III кв. 26 – II кв. 27, очередь 1, 573 / 1 900, ФР 18.6, LLCR 1.20', async ({ page }) => {
  await openDashboard(page)
  await expect(page.locator('.main-title')).toHaveText('СОКОЛЬНИКИ 09 09 NEW FM В РЫНКЕ')
  await expect(page.locator('svg[data-chart="price"] g[data-quarter]')).toHaveCount(4)
  await expect(page.locator('svg[data-chart="price"] g[data-quarter]').first()).toHaveAttribute('data-quarter', 'III кв. 26')
  await expect(page.locator('svg[data-chart="price"] g[data-quarter]').last()).toHaveAttribute('data-quarter', 'II кв. 27')
  await expect(page.getByTestId('price-val')).toHaveText('573')
  await expect(page.getByTestId('pace-val')).toHaveText('1 900')
  await expect(page.getByTestId('fr')).toHaveText('18.6')
  await expect(page.getByTestId('llcr')).toHaveText('1.20')
  await expect(oursLabels(page, 'price')).toHaveText(['573', '586', '607', '622'])
  await expect(oursLabels(page, 'pace')).toHaveText(['1.9', '2.4', '2.0', '2.6'])
})

test('цена +3 → 603 и пересчёт ФР/LLCR моделью; сброс', async ({ page }) => {
  await openDashboard(page)
  const plus = page.getByRole('button', { name: 'Цена +10' })
  for (let i = 0; i < 3; i++) await plus.click()
  await expect(page.getByTestId('price-val')).toHaveText('603')
  await expect(oursLabels(page, 'price')).toHaveText(['603', '617', '639', '655'])
  await expect(page.locator('svg[data-chart="price"] .base-mark')).toHaveCount(4)
  await expect(page.getByTestId('calc-state')).toHaveText('пересчёт модели…')
  await expect(page.getByTestId('calc-state')).toHaveText('', { timeout: 60_000 })
  await expect(page.getByTestId('fr')).toHaveText('19.7')
  await expect(page.getByTestId('llcr')).toHaveText('1.19')
  await expect(page.locator('.kpi .d.up')).toHaveText('+1.2 к модели')

  await page.getByRole('button', { name: 'Сбросить' }).click()
  await expect(page.getByTestId('price-val')).toHaveText('573')
  await expect(page.getByTestId('fr')).toHaveText('18.6')
  await expect(page.locator('.kpi .d').first()).toHaveText('значение модели')
})

test('темп +5 → 2 400 м², пересчёт без ошибок', async ({ page }) => {
  await openDashboard(page)
  const plus = page.getByRole('button', { name: 'Темп +100' })
  for (let i = 0; i < 5; i++) await plus.click()
  await expect(page.getByTestId('pace-val')).toHaveText('2 400')
  await expect(page.getByTestId('calc-state')).toHaveText('', { timeout: 60_000 })
  await expect(page.getByTestId('fr')).toHaveText('18.5')
})

test('очереди, чипы и навигация по кварталам', async ({ page }) => {
  await openDashboard(page)
  await page.getByRole('button', { name: 'Весь проект' }).click()
  await expect(page.getByRole('slider', { name: 'Цена 1 м²' })).toBeDisabled()
  // очередь 2 стартует во II кв. 27 — якорь ползунков смещается на него
  await page.getByRole('button', { name: '2', exact: true }).click()
  await expect(page.getByTestId('price-val')).toHaveText('572')
  await expect(page.getByText(/^II кв\. 27 · Продажи!Z58$/)).toBeVisible()
  await page.getByRole('button', { name: '3', exact: true }).click()
  await expect(page.getByText(/очередь 3 не в продаже/)).toBeVisible()

  await page.getByRole('button', { name: '1', exact: true }).click()
  const ahead = page.locator('svg[data-chart="price"] g.bar[data-name="AHEAD"]')
  await expect(ahead).toHaveCount(0)
  await page.getByRole('button', { name: /AHEAD/ }).click()
  await expect(ahead).toHaveCount(4)
  await page.getByRole('button', { name: /AHEAD/ }).click()
  await expect(ahead).toHaveCount(0)

  await page.getByRole('button', { name: /Следующий квартал/ }).click()
  await expect(page.locator('svg[data-chart="price"] g[data-quarter]').first()).toHaveAttribute('data-quarter', 'IV кв. 26')
  await page.getByRole('button', { name: 'В начало' }).click()
  await expect(page.locator('svg[data-chart="price"] g[data-quarter]').first()).toHaveAttribute('data-quarter', 'I кв. 26')
  await expect(page.getByRole('button', { name: /Предыдущий квартал/ })).toBeDisabled()
})
