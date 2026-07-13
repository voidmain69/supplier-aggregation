/**
 * Flat Ukrainian string dictionary. The UI ships one locale (curation-ui-plan §9.2), so a full
 * i18n framework is overkill — but keeping copy out of components means we can add one later
 * without touching JSX. Keys are English; values are Ukrainian.
 */

export const t = {
  appName: 'Курація матчингу',
  nav: {
    queue: 'Черга',
    canonical: 'Канонічні товари',
    signOut: 'Вийти',
  },
  login: {
    title: 'Вхід куратора',
    tokenLabel: 'Токен доступу (Bearer)',
    tokenHint: 'Токен видає адміністратор платформи. Зберігається лише в цій вкладці.',
    submit: 'Увійти',
    checking: 'Перевірка…',
    invalid: 'Токен недійсний або бракує скоупа matching:curate.',
  },
  queue: {
    title: 'Черга курації',
    empty: 'Чергу розібрано 🎉',
    emptyHint: 'Нових пропозицій матчингу немає.',
    loadMore: 'Завантажити ще',
    depth: (n: number | string) => `${String(n)} у черзі`,
    filters: { all: 'Усі', rag: 'RAG-кандидати', collision: 'GTIN-колізії' },
    columns: {
      product: 'Товар постачальника',
      candidate: 'Кандидат',
      method: 'Метод',
      confidence: 'Впевненість',
      age: 'У черзі',
    },
    open: 'Відкрити',
  },
  review: {
    supplierSide: 'Товар постачальника',
    candidateSide: 'Кандидат (канонічний)',
    diff: 'Порівняння атрибутів',
    linkedProducts: 'Лінковані товари',
    commercial: 'Комерційний контекст',
    offers: 'Офери',
    priceHistory: 'Історія ціни',
    noOffers: 'Активних оферів немає.',
    confirm: 'Підтвердити',
    reject: 'Відхилити',
    skip: 'Пропустити',
    back: 'До черги',
    confirmed: 'Підтверджено',
    rejected: 'Відхилено',
    alreadyDecided: (status: string) => `Лінк уже вирішено: ${status}`,
    decidedByYou: 'Рішення прийнято',
  },
  canonical: {
    title: 'Канонічні товари',
    searchGtin: 'Пошук за GTIN-14',
    empty: 'Нічого не знайдено.',
    status: { draft: 'Чернетка', confirmed: 'Підтверджено' },
  },
  common: {
    retry: 'Повторити',
    loading: 'Завантаження…',
    errorTitle: 'Сталася помилка',
    traceHint: 'Повідомте цей код підтримці:',
    gtin: 'GTIN',
    brand: 'Бренд',
    mpn: 'Артикул (MPN)',
    supplier: 'Постачальник',
    category: 'Категорія',
    attributes: 'Характеристики',
    none: '—',
  },
  method: {
    gtin_auto: 'GTIN (авто)',
    rag_suggested: 'RAG',
    manual: 'Вручну',
  } as Record<string, string>,
} as const;
