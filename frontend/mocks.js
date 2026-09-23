// Зафиксированные ответы backend для демонстрации интерфейса; не подбор на фронте.
export const MOCK_FILTERS = {
  "cities": [
    "Алматы",
    "Астана",
    "Зарубежье"
  ],
  "categories": [
    "Банкетный зал",
    "Ведущий",
    "Ведущий церемонии",
    "Видеограф",
    "Декоратор",
    "Загородная площадка",
    "Инструменталист",
    "Лайв-бэнд",
    "Национальный ансамбль",
    "Отель",
    "Подарки и сувениры",
    "Ресторан",
    "Танцевальный коллектив",
    "Флорист",
    "Фото и видеобудки",
    "Фотограф",
    "Шоу-программа"
  ],
  "event_formats": [
    "день рождения",
    "конференция",
    "корпоратив",
    "свадьба",
    "той",
    "юбилей"
  ],
  "languages": [
    "английский",
    "казахский",
    "русский"
  ],
  "event_date_range": {
    "min": "2026-09-23",
    "max": "2026-12-31"
  }
};
export const MOCK_REQUESTS = {
  "success": {
    "city": "Алматы",
    "event_date": "2026-10-07",
    "event_format": "свадьба",
    "category": "Ведущий",
    "budget_kzt": 1000000,
    "duration_hours": null,
    "language": "казахский"
  },
  "rare": {
    "city": "Алматы",
    "event_date": "2026-10-04",
    "event_format": "свадьба",
    "category": "Флорист",
    "budget_kzt": 250000,
    "duration_hours": null,
    "language": "русский"
  },
  "no_category": {
    "city": "Зарубежье",
    "event_date": "2026-10-07",
    "event_format": "свадьба",
    "category": "Флорист",
    "budget_kzt": 1000000,
    "duration_hours": null,
    "language": "казахский"
  },
  "no_match": {
    "city": "Алматы",
    "event_date": "2026-10-04",
    "event_format": "свадьба",
    "category": "Флорист",
    "budget_kzt": 100000,
    "duration_hours": null,
    "language": "русский"
  }
};
export const MOCK_RESPONSES = {
  "success": {
    "outcome": "matches",
    "cards": [
      {
        "id": "HK-35215",
        "name": "Кики",
        "categories": [
          "Ведущий"
        ],
        "city": "Алматы",
        "price_from_kzt": 900000,
        "synthetic": false,
        "city_imputed": false,
        "price_imputed": false,
        "explanation": "Свободен 2026-10-07 и берёт формат «свадьба», работает на казахский. Цена от 900 000 ₸ укладывается в бюджет 1 000 000 ₸; в профиле отмечено: «Кики — редкое сочетание тонкого юмора, харизмы и безупречных манер»."
      },
      {
        "id": "HK-42352",
        "name": "Эмилия",
        "categories": [
          "Ведущий"
        ],
        "city": "Алматы",
        "price_from_kzt": 900000,
        "synthetic": false,
        "city_imputed": false,
        "price_imputed": true,
        "explanation": "Свободен 2026-10-07 и берёт формат «свадьба», работает на казахский. Цена от 900 000 ₸ укладывается в бюджет 1 000 000 ₸; в профиле отмечено: «Опыт ведения свадеб 13 лет Вел свадьбы в Алматы, Москве, Дубае, Бодруме, Ташкенте Статистика: 356 свадеб, 0…»."
      },
      {
        "id": "HK-27222",
        "name": "Сон Гоку",
        "categories": [
          "Ведущий"
        ],
        "city": "Алматы",
        "price_from_kzt": 1000000,
        "synthetic": false,
        "city_imputed": false,
        "price_imputed": false,
        "explanation": "Свободен 2026-10-07 и берёт формат «свадьба», работает на казахский. Цена от 1 000 000 ₸ укладывается в бюджет 1 000 000 ₸; в профиле отмечено: «Сон Гоку — один из самых востребованных двуязычных ведущих Алматы с опытом более 12 лет»."
      }
    ],
    "message": "Подобрано 3 из 4 подходящих подрядчиков.",
    "stats": {
      "catalog_candidates": 10,
      "eligible": 4,
      "rejected": {
        "busy": 1,
        "format": 4,
        "language": 5,
        "budget": 2
      }
    }
  },
  "rare": {
    "outcome": "matches",
    "cards": [
      {
        "id": "HK-39372",
        "name": "Тони Тони Чоппер",
        "categories": [
          "Флорист"
        ],
        "city": "Алматы",
        "price_from_kzt": 200000,
        "synthetic": false,
        "city_imputed": false,
        "price_imputed": true,
        "explanation": "Свободен 2026-10-04 и берёт формат «свадьба», работает на русский. Цена от 200 000 ₸ укладывается в бюджет 250 000 ₸; в профиле отмечено: «Мы специализируемся на авторском цветочном оформлении и флористике для мероприятий в Алматы»."
      },
      {
        "id": "HK-90001",
        "name": "Тихиро Огино",
        "categories": [
          "Флорист"
        ],
        "city": "Алматы",
        "price_from_kzt": 250000,
        "synthetic": true,
        "city_imputed": false,
        "price_imputed": false,
        "explanation": "Свободен 2026-10-04 и берёт формат «свадьба», работает на русский. Цена от 250 000 ₸ укладывается в бюджет 250 000 ₸; в профиле отмечено: «White Sakura Studio — авторская флористика для свадеб и юбилеев»."
      }
    ],
    "message": "Подобрано 2 из 2 подходящих подрядчиков. Меньше трёх, потому что в этой категории всего столько доступных профилей.",
    "stats": {
      "catalog_candidates": 2,
      "eligible": 2,
      "rejected": {}
    }
  },
  "no_category": {
    "outcome": "category_absent",
    "cards": [],
    "message": "В городе «Зарубежье» нет подрядчиков категории «Флорист».",
    "stats": {
      "catalog_candidates": 0,
      "eligible": 0,
      "rejected": {}
    }
  },
  "no_match": {
    "outcome": "no_match",
    "cards": [],
    "message": "В каталоге есть 2 подрядчик(а) этой категории, но никто не проходит условия: 2 не укладываются в бюджет.",
    "stats": {
      "catalog_candidates": 2,
      "eligible": 0,
      "rejected": {
        "budget": 2
      }
    }
  }
};
