# Документація по API BRAIN

Компанія BRAIN надає для своїх партнерів доступ до бази даних товарів через API. Для отримання доступу до інтерфейсу достатньо мати активовану реєстрацію на оптовому порталі компанії зі статусом Адміністратор.

За допомогою API BRAIN Ви зможете отримати прайси, каталог товарів, ціни, наявність, характеристики, опис, фільтри, а також забронювати товар, сформувати, відвантажити замовлення та багато іншого.

**Базовий URL:** `http://api.brain.com.ua`  
**Частота запитів:** не більше **3 запитів на секунду**. При перевищенні — відповідь `429 Too Many Requests` і помилка 115.

**Підтримка:** support_b2b@brain.ua

---

## Зміст

1. [Аутентифікація](#1-аутентифікація)
   - [auth](#auth)
   - [logout](#logout)
2. [Каталог товарів](#2-каталог-товарів)
   - [products](#products)
   - [product](#product)
   - [product/articul](#productarticul)
   - [product/product_code](#productproduct_code)
   - [categories](#categories)
   - [vendors](#vendors)
   - [content](#content)
   - [modified_products](#modified_products)
   - [product_options](#product_options)
   - [product_pictures](#product_pictures)
   - [products_pictures](#products_pictures)
   - [comments](#comments)
   - [filters](#filters)
   - [filters_all](#filters_all)
3. [Доступність товарів](#3-доступність-товарів)
   - [delivery_time](#delivery_time)
   - [delivery_time/product_code](#delivery_timeproduct_code)
   - [targets](#targets)
   - [discounted_targets](#discounted_targets)
   - [addresses](#addresses)
   - [stocks](#stocks)
4. [Робота із замовленнями](#4-робота-із-замовленнями)
   - [GET order](#get-order)
   - [POST order](#post-order)
   - [POST order/delete](#post-orderdelete)
   - [clear_cart](#clear_cart)
   - [put_order](#put_order)
   - [reserve_order](#reserve_order)
   - [ship_order](#ship_order)
   - [close_order](#close_order)
   - [orders](#orders)
5. [Механізм комісійного продажу](#5-механізм-комісійного-продажу)
   - [add_recipient](#add_recipient)
   - [ship_order_to_recipient](#ship_order_to_recipient)
6. [Дропшипінг](#6-дропшипінг)
   - [ship_order_to_drop](#ship_order_to_drop)
7. [Звіти](#7-звіти)
   - [report](#report)
8. [Прайс-листи](#8-прайс-листи)
   - [pricelists](#pricelists)
   - [discounted_pricelists](#discounted_pricelists)
9. [Додатково](#9-додатково)
   - [currencies](#currencies)
   - [contacts](#contacts)
10. [Термінологія](#10-термінологія)
11. [Помилки та коди помилок](#11-помилки-та-коди-помилок)
12. [Формування URL для зображення товару](#12-формування-url-для-зображення-товару)

---

## 1. Аутентифікація

### auth

**URL:** `http://api.brain.com.ua/auth`  
**HTTP Метод:** `POST`

**Опис:** Метод для отримання ідентифікатора сесії.

**Параметри:**

| Назва параметра | Обов'язковий | Опис |
|---|---|---|
| login | так | логін користувача дилерського порталу з правами керівника (адміністратора) |
| password | так | пароль користувача захешований MD5 функцією |

**Результат:** Метод повертає ідентифікатор сесії (SID), який необхідний для реалізації наступних запитів.

**Приклад відповіді:**
```json
{"status":1,"result":"gpkavk4s0aciujg6m698gev040"}
```

---

### logout

**URL:** `http://api.brain.com.ua/logout/SID`  
**HTTP Метод:** `POST`

**Опис:** Метод ліквідації поточної сесії.

**Параметри:**

| Назва параметра | Обов'язковий | Опис |
|---|---|---|
| SID | так | ідентифікатор сесії |

**Результат:** Відбувається закінчення поточної сесії.

**Приклад відповіді:**
```json
{"status":1,"result":"1"}
```

---

## 2. Каталог товарів

### products

**URL:** `http://api.brain.com.ua/products/categoryID/SID`  
**Необов'язкові параметри URL:** `[?vendorID=vendorID][&search=search][&filterID=filterID][&filters[]=filterID][&limit=limit][&offset=offset][&sortby=field_name][&order=order][&lang=lang]`  
**HTTP Метод:** `GET`

**Опис:** Метод отримання списку товарів зазначеної категорії та всіх її дочірніх категорій.

**Параметри:**

| Назва параметра | Обов'язковий | Опис |
|---|---|---|
| categoryID | так | ідентифікатор категорії |
| SID | так | ідентифікатор сесії |
| lang | ні | мова, можливі значення — `ua` та `ru`, за замовчуванням `ua` |
| vendorID | ні | ідентифікатор виробника |
| search | ні | рядок пошуку |
| filterID | ні | ідентифікатор фільтра |
| filters[] | ні | масив ідентифікаторів фільтрів |
| limit | ні | кількість товарів (без OWN_MODE: макс. 100, за замовч. 100; з OWN_MODE: макс. 1000, за замовч. 1000) |
| offset | ні | кількість товарів, що пропускаються перед виведенням результатів; за замовчуванням 0 |
| sortby | ні | поле сортування: `name`, `brief_description`, `productID`, `product_code`, `warranty`, `is_archive`, `vendorID`, `articul`, `volume`, `is_new`, `categoryID`; за замовч. `productID` |
| order | ні | порядок сортування: `asc` або `desc`; за замовч. `asc` |

**Пошуковий рядок може бути двох видів:**

1. Рядок тексту — пошук по рядку цілком:
```
http://api.brain.com.ua/products/125/SID?search=apple macbook pro
→ LIKE '%apple macbook pro%'
```

2. JSON-рядок — складений пошуковий запит:
```
http://api.brain.com.ua/products/125/SID?lang=ua&search={"and":["appl",{"or":["pro","mini","i7"]}]}
→ LIKE '%appl%' AND (LIKE '%pro%' OR LIKE '%mini%' OR LIKE '%i7%')
```

> Для фільтрації можна використовувати `filterID` або масив `filters[]`. Якщо вказані обидва — об'єднуються.
> Значення `stocks`, `stocks_expected` і `available` повертаються лише для користувачів зі статусом `OWN_LOGISTICS_MODE`.
> Параметр `count` показує кількість товарів без урахування `offset` і `limit`.

**Приклад відповіді:**
```json
{
  "status": 1,
  "result": {
        "productID": 100463720,
        "product_code": "U1005797",
        "date_added": "2025-01-03 07:31:22",
        "date_modified": "2026-07-11 09:26:36",
        "actionID": 0,
        "warranty": "36",
        "is_archive": false,
        "is_exclusive": true,
        "vendorID": 5,
        "articul": "TUF GAMING B850-PLUS WIFI",
        "volume": 0.01,
        "weight": 2.5,
        "kbt": 0,
        "is_price_cut": false,
        "is_new": false,
        "EAN": "4711387781609",
        "reservation_limit": 0,
        "non_returnable": 0,
        "name": "Материнська плата ASUS TUF GAMING B850-PLUS WIFI",
        "brief_description": "сокет - AM5, чіпсет - AMD B850, DDR5, макс. об'єм оперативної пам'яті - 192 ГБ, макс. частота оперативної пам'яті - 8000 MHz, швидкість LAN - 2,5 Гбіт/с, DisplayPort, HDMI, внутрішні - 1 x M.2 22110, 2 x M.2 2280, 4 x Sata 6.0 Gb/s, Bluetooth 5.4, Intel Wi-Fi 7 2x2 Wi-Fi 7 (802.11be), ATX",
        "description": "Материнська плата <b>ASUS TUF GAMING B850-PLUS WIFI</b> розроблена для тих, хто цінує високу продуктивність та стабільність під час гри чи роботи з ресурсомісткими додатками. В основі цієї плати — потужний <b>чіпсет AMD B850</b>, який підтримує новітні процесори AMD Ryzen™. Завдяки сучасній підтримці <b>DDR5 пам’яті</b>, максимальний обсяг якої може сягати 192 ГБ, ви зможете насолоджуватися швидкістю роботи на частотах до 8000 MHz, що є чудовим вибором для геймерів та творчих фахівців. Двоканальний режим пам’яті покращить її ефективність та дозволить швидше обробляти великі обсяги даних.<br><br>Інноваційна система живлення материнської плати є високотехнологічним рішенням для забезпечення стабільної роботи комп’ютера. Вона оснащена 14 (80A) + 2 (80A) + 1 (80A) каскадами живлення, що дозволяє з легкістю справлятися з високими навантаженнями. Це не лише підвищує загальну продуктивність системи, але й забезпечує довготривалу стабільність та надійність.<br><br>Плата славиться своїми потужними можливостями розширення завдяки <b>2 слотам PCI Express x16</b> та <b>2 слотам PCI Express x1</b>. Ця конфігурація дає змогу підключити найновіші відеокарти та інші розширювальні пристрої, розширюючи можливості вашого ПК. Вражаючий набір <b>зовнішніх портів</b> включає 5 аудіо виходів, 1 Wi-Fi модуль, HDMI, DisplayPort та багато інших, що дозволяє легко інтегрувати систему з різноманітними периферійними пристроями.<br><br>Інтегрований <b>аудіоконтролер Realtek ALC1220P</b> забезпечує чудову якість звуку завдяки підтримці багатоканального аудіо, що буде відчутною перевагою для геймерів та прихильників мультимедіа. У грі чи під час перегляду фільмів ви отримаєте більш захоплюючий і реалістичний звуковий досвід.<br><br><b>Мережева карта Realtek 2.5GbE</b> гарантує швидкість передачі даних до 2,5 Гбіт/с, що дозволяє ефективно працювати в домашній або офісній мережі. Безпровідні технології, такі як <b>Bluetooth 5.4</b> та <b>Intel Wi-Fi 7</b>, забезпечують бездоганний зв'язок, дозволяючи залишатися на зв’язку в різних умовах бездротового підключення. Ці рішення дозволять вам зануритися в онлайн-ігри без затримок або переглядати відео у високій якості.<br><br><b>RAID-контролер</b> надає можливість створення надійної конфігурації з п’яти різних видів: 10, 5, 1 та 0. Це дозволяє забезпечити додатковий захист ваших даних. Інтерфейси <b>M.2</b> в кількості трьох та чотири <b>порти SATA 6.0 Gb/s</b> створюють величезні можливості для підключення швидкісних накопичувачів, що підвищує загальну продуктивність вашої системи.<br><br>Материнська плата має підтримку <b>Windows 11</b>, що дозволяє користуватися всіма перевагами нової операційної системи, включаючи нові функції безпеки та зручний інтерфейс користувача. Її <b>форм-фактор ATX</b> забезпечує легке встановлення в більшості корпусів, даючи можливість створити систему, ідеально підібрану під ваші потреби.<br><br>Більше того, плата <b>ASUS TUF GAMING B850-PLUS WIFI</b> вирізняється підвищеною надійністю завдяки використанню компонентів військового класу та інноваційної системи охолодження. Кожна деталь пройшла ретельні випробування на довговічність, щоб гарантувати, що вона зможе витримувати найскладніші умови використання. Це робить її відмінним вибором для геймерів, які шукають стабільність і продуктивність в одному рішенні. Насолоджуйтеся грою на новому рівні, зосереджуючись на тому, що для вас дійсно важливо.",
        "country": "Китай",
        "categoryID": 1264,
        "FOP": 0,
        "price": "222.22",
        "price_uah": "9900.00",
        "recommendable_price": "0.00",
        "retail_price_uah": "9999.00",
        "prepayment_amount": 0,
        "bonus": 120,
        "stocks": [
            1,
            121,
            168,
            258
        ],
        "stocks_expected": {
            "19": "2026-07-15 07:30:00",
            "29": "2026-07-13 16:00:00",
            "42": "2026-07-13 17:30:00",
            "58": "2026-07-13 14:00:00",
            "144": "2026-07-14 12:00:00",
            "172": "2026-07-14 13:00:00",
            "225": "2026-07-13 14:00:00",
            "245": "2026-07-13 16:00:00",
            "643": "2026-07-14 12:00:00",
            "1001": "2026-07-14 18:00:00",
            "1002": "2026-07-11 19:01:00",
            "1003": "2026-07-13 18:00:00"
        },
        "available": {
            "1": 3,
            "121": 2,
            "168": 1,
            "258": 1
        },
        "self_delivery": "1",
        "small_image": "https://opt.brain.com.ua/static/images/prod_img/9/7/U1005797_small.jpg",
        "medium_image": "https://opt.brain.com.ua/static/images/prod_img/9/7/U1005797.jpg",
        "large_image": "https://opt.brain.com.ua/static/images/prod_img/9/7/U1005797_big.jpg",
        "full_image": "https://opt.brain.com.ua/static/images/prod_img/9/7/U1005797_main.jpg",
        "quantity_package_sale": 0,
        "koduktved": "8473302000",
        "options": [
            {
                "name": "Виробник",
                "value": "ASUS",
                "optionID": "3"
            },
            {
                "name": "Модель",
                "value": "TUF GAMING B850-PLUS WIFI",
                "optionID": "1"
            },
            {
                "name": "Артикул",
                "value": "TUF GAMING B850-PLUS WIFI",
                "optionID": "2"
            },
            {
                "name": "Призначення",
                "value": "геймерська",
                "optionID": "11151",
                "valueID": "86023957900"
            },
            {
                "name": "Сокет",
                "value": "AM5",
                "optionID": "1388",
                "valueID": "86083556200"
            },
            {
                "name": "Підтримка процесорів",
                "value": "AMD Socket AM5 for AMD Ryzen 9000 & 8000 & 7000 Series Desktop Processors",
                "optionID": "11189",
                "valueID": "86078250000"
            },
            {
                "name": "Слоти розширення",
                "value": "1 x PCI-E 4.0 x16",
                "optionID": "1383",
                "valueID": "86037399200"
            },
            {
                "name": "Слоти розширення",
                "value": "2 x PCI-E 4.0 x1",
                "optionID": "1383",
                "valueID": "86039853600"
            },
            {
                "name": "Слоти розширення",
                "value": "1 x PCI-E 5.0 x16",
                "optionID": "1383",
                "valueID": "86050764700"
            },
            {
                "name": "PCI Express x1",
                "value": "2 шт",
                "optionID": "24347",
                "valueID": "86050075700"
            },
            {
                "name": "PCI Express x16",
                "value": "2 шт",
                "optionID": "24350",
                "valueID": "86050186400"
            },
            {
                "name": "PCI",
                "value": "без слота PCI",
                "optionID": "24351",
                "valueID": "86050187600"
            },
            {
                "name": "(Збірка) Тип слота PCI 1",
                "value": "M.2 2280",
                "optionID": "19553",
                "valueID": "86043231700"
            },
            {
                "name": "(Збірка) Тип слота PCI 2",
                "value": "PCIe x16",
                "optionID": "19554",
                "valueID": "86043108800"
            },
            {
                "name": "(Збірка) Тип слота PCI 3",
                "value": "Пустий",
                "optionID": "19555",
                "valueID": "86043237500"
            },
            {
                "name": "(Збірка) Тип слота PCI 4",
                "value": "PCIe x1",
                "optionID": "19556",
                "valueID": "86043240300"
            },
            {
                "name": "(Збірка) Тип слота PCI 5",
                "value": "PCIe x16",
                "optionID": "19557",
                "valueID": "86043108900"
            },
            {
                "name": "(Збірка) Тип слота PCI 6",
                "value": "M.2 22110",
                "optionID": "19558",
                "valueID": "86043236000"
            },
            {
                "name": "(Збірка) Тип слота PCI 7",
                "value": "PCIe x1",
                "optionID": "19559",
                "valueID": "86043238800"
            },
            {
                "name": "Модель чіпсета",
                "value": "AMD B850",
                "optionID": "11160",
                "valueID": "86078250100"
            },
            {
                "name": "Тип оперативної пам'яті",
                "value": "DDR5",
                "optionID": "11161",
                "valueID": "86050768600"
            },
            {
                "name": "Кількість роз'ємів оперативної пам'яті",
                "value": "4 шт",
                "optionID": "11163",
                "valueID": "86023987600"
            },
            {
                "name": "Максимальний об'єм оперативної пам'яті",
                "value": "192 ГБ",
                "optionID": "1379",
                "valueID": "86063698900"
            },
            {
                "name": "Максимальна частота оперативної пам'яті",
                "value": "8000 MHz",
                "optionID": "24309",
                "valueID": "86061939400"
            },
            {
                "name": "Підтримка двоканального режиму",
                "value": "так",
                "optionID": "11164",
                "valueID": "86023961700"
            },
            {
                "name": "Вбудоване відео",
                "value": "З підтримкою відеоядра процесора",
                "optionID": "24296",
                "valueID": "86049992000"
            },
            {
                "name": "Аудіоконтролер",
                "value": "Realtek ALC1220P",
                "optionID": "11172",
                "valueID": "86034104700"
            },
            {
                "name": "Багатоканальний звук",
                "value": "7.1",
                "optionID": "11174",
                "valueID": "86023962700"
            },
            {
                "name": "Кількість LAN портів",
                "value": "1 шт",
                "optionID": "11176",
                "valueID": "86023962900"
            },
            {
                "name": "Тип мережевої карти",
                "value": "Realtek 2.5GbE",
                "optionID": "11177",
                "valueID": "86045466600"
            },
            {
                "name": "Швидкість LAN портів",
                "value": "2,5 Гбіт/с",
                "optionID": "11178",
                "valueID": "86037468400"
            },
            {
                "name": "Зовнішні порти",
                "value": "1 x BIOS FlashBack Button",
                "optionID": "1386",
                "valueID": "86043442500"
            },
            {
                "name": "Зовнішні порти",
                "value": "1 x Wi-Fi Module",
                "optionID": "1386",
                "valueID": "86050799100"
            },
            {
                "name": "Зовнішні порти",
                "value": "1 x USB 20Gbps port (1 x USB Type-C)",
                "optionID": "1386",
                "valueID": "86070221900"
            },
            {
                "name": "Зовнішні порти",
                "value": "4 x USB 5Gbps ports (4 x Type-A)",
                "optionID": "1386",
                "valueID": "86070222100"
            },
            {
                "name": "Зовнішні порти",
                "value": "3 x USB 10Gbps",
                "optionID": "1386",
                "valueID": "86075381000"
            },
            {
                "name": "Зовнішні порти",
                "value": "1 x RJ45",
                "optionID": "1386",
                "valueID": "86003774300"
            },
            {
                "name": "Зовнішні порти",
                "value": "2 x USB 2.0",
                "optionID": "1386",
                "valueID": "86003772600"
            },
            {
                "name": "Зовнішні порти",
                "value": "1 x HDMI",
                "optionID": "1386",
                "valueID": "86003775000"
            },
            {
                "name": "Зовнішні порти",
                "value": "1 x DisplayPort",
                "optionID": "1386",
                "valueID": "86003772700"
            },
            {
                "name": "Зовнішні порти",
                "value": "5 x Audio",
                "optionID": "1386",
                "valueID": "86003773300"
            },
            {
                "name": "Відеовиходи",
                "value": "DisplayPort",
                "optionID": "24304",
                "valueID": "86050013600"
            },
            {
                "name": "Відеовиходи",
                "value": "HDMI",
                "optionID": "24304",
                "valueID": "86050013700"
            },
            {
                "name": "USB",
                "value": "USB Type-C",
                "optionID": "24305",
                "valueID": "86050014600"
            },
            {
                "name": "USB",
                "value": "USB 2.0",
                "optionID": "24305",
                "valueID": "86050014200"
            },
            {
                "name": "USB",
                "value": "USB 3.2",
                "optionID": "24305",
                "valueID": "86050014500"
            },
            {
                "name": "Цифровий аудіо роз'єм (S/PDIF)",
                "value": "без цифрового аудіо виходу",
                "optionID": "24306",
                "valueID": "86050015000"
            },
            {
                "name": "Внутрішні роз'єми і порти",
                "value": "1 x M.2 22110",
                "optionID": "1384",
                "valueID": "86043740700"
            },
            {
                "name": "Внутрішні роз'єми і порти",
                "value": "2 x M.2 2280",
                "optionID": "1384",
                "valueID": "86043957800"
            },
            {
                "name": "Внутрішні роз'єми і порти",
                "value": "4 x Sata 6.0 Gb/s",
                "optionID": "1384",
                "valueID": "86003776300"
            },
            {
                "name": "M.2",
                "value": "3 шт.",
                "optionID": "24307",
                "valueID": "86050015700"
            },
            {
                "name": "Кількість SATA-III портів",
                "value": "4 шт.",
                "optionID": "24308",
                "valueID": "86050016500"
            },
            {
                "name": "SATAe роз'єм",
                "value": "без SATAe інтерфейсу",
                "optionID": "24467",
                "valueID": "86050325200"
            },
            {
                "name": "U.2 роз'єм",
                "value": "без U.2 роз'єму",
                "optionID": "24466",
                "valueID": "86050325000"
            },
            {
                "name": "Конектор живлення",
                "value": "1 x 24-pin Main Power",
                "optionID": "11181",
                "valueID": "86069164600"
            },
            {
                "name": "Конектор живлення",
                "value": "2 x 8-pin +12V Power",
                "optionID": "11181",
                "valueID": "86069164700"
            },
            {
                "name": "Колодки",
                "value": "2 x USB 2.0",
                "optionID": "11179",
                "valueID": "86023966000"
            },
            {
                "name": "Колодки",
                "value": "1 x USB 5Gbps",
                "optionID": "11179",
                "valueID": "86071402700"
            },
            {
                "name": "Колодки",
                "value": "1 x USB 10Gbps Type C",
                "optionID": "11179",
                "valueID": "86075381300"
            },
            {
                "name": "4-pin для вентилятора",
                "value": "4 шт.",
                "optionID": "11183",
                "valueID": "86023986800"
            },
            {
                "name": "Інші коннектори",
                "value": "1 x COM port header",
                "optionID": "11184",
                "valueID": "86024017700"
            },
            {
                "name": "Інші коннектори",
                "value": "1 x Chassis intrusion header",
                "optionID": "11184",
                "valueID": "86024090400"
            },
            {
                "name": "Інші коннектори",
                "value": "1 x 4-pin CPU Fan header",
                "optionID": "11184",
                "valueID": "86045806500"
            },
            {
                "name": "Інші коннектори",
                "value": "1 x 4-pin CPU OPT Fan header",
                "optionID": "11184",
                "valueID": "86045806600"
            },
            {
                "name": "Інші коннектори",
                "value": "1 x 4-pin AIO Pump header",
                "optionID": "11184",
                "valueID": "86045806700"
            },
            {
                "name": "Інші коннектори",
                "value": "1 x Clear CMOS header",
                "optionID": "11184",
                "valueID": "86045807200"
            },
            {
                "name": "Інші коннектори",
                "value": "3 x Addressable Gen 2 headers",
                "optionID": "11184",
                "valueID": "86050767600"
            },
            {
                "name": "Інші коннектори",
                "value": "4 x 4-pin Chassis Fan headers",
                "optionID": "11184",
                "valueID": "86057769800"
            },
            {
                "name": "Інші коннектори",
                "value": "1 x Thunderbolt (USB4) header",
                "optionID": "11184",
                "valueID": "86070223100"
            },
            {
                "name": "Інші коннектори",
                "value": "1 x Front panel audio header (F_AUDIO)",
                "optionID": "11184",
                "valueID": "86070223300"
            },
            {
                "name": "Інші коннектори",
                "value": "1 x 10-1 pin Front System Panel header",
                "optionID": "11184",
                "valueID": "86075996200"
            },
            {
                "name": "Тип BIOS",
                "value": "256 Mb Flash ROM, UEFI AMI BIOS",
                "optionID": "11185",
                "valueID": "86046896600"
            },
            {
                "name": "Бездротовий зв'язок",
                "value": "Bluetooth 5.4",
                "optionID": "11186",
                "valueID": "86070222400"
            },
            {
                "name": "Бездротовий зв'язок",
                "value": "Intel Wi-Fi 7 2x2 Wi-Fi 7 (802.11be)",
                "optionID": "11186",
                "valueID": "86070222500"
            },
            {
                "name": "Контролер RAID",
                "value": "0",
                "optionID": "1385",
                "valueID": "86050106200"
            },
            {
                "name": "Контролер RAID",
                "value": "1",
                "optionID": "1385",
                "valueID": "86050106300"
            },
            {
                "name": "Контролер RAID",
                "value": "5",
                "optionID": "1385",
                "valueID": "86050106400"
            },
            {
                "name": "Контролер RAID",
                "value": "10",
                "optionID": "1385",
                "valueID": "86050106600"
            },
            {
                "name": "Підтримка ОС",
                "value": "Windows 11",
                "optionID": "15665",
                "valueID": "86049445800"
            },
            {
                "name": "Також шукають",
                "value": "материнська плата для ПК",
                "optionID": "11150",
                "valueID": "86023957600"
            },
            {
                "name": "Форм-фактор",
                "value": "ATX",
                "optionID": "1376",
                "valueID": "86003740400"
            },
            {
                "name": "Висота, мм",
                "value": "305",
                "optionID": "11187",
                "valueID": "86023990600"
            },
            {
                "name": "Ширина, мм",
                "value": "244",
                "optionID": "11188",
                "valueID": "86023987800"
            },
            {
                "name": "(Збірка) Споживча потужність",
                "value": "35 Вт",
                "optionID": "19552",
                "valueID": "86043200400"
            },
            {
                "name": "PCI Express x1 ver",
                "value": "2 v Чотири",
                "optionID": "25024",
                "valueID": "86051485500"
            },
            {
                "name": "PCI Express x16 ver",
                "value": "1 v Чотири",
                "optionID": "24902",
                "valueID": "86051170800"
            },
            {
                "name": "PCI Express x16 ver",
                "value": "1 v П'ять",
                "optionID": "24902",
                "valueID": "86051171000"
            },
            {
                "name": "M.2 ver",
                "value": "1 x M.II",
                "optionID": "25308",
                "valueID": "86051531100"
            },
            {
                "name": "M.2 ver",
                "value": "2 x M.II",
                "optionID": "25308",
                "valueID": "86051531200"
            },
            {
                "name": "Країна виробництва",
                "value": "Китай",
                "optionID": "5"
            },
            {
                "name": "Гарантія, міс",
                "value": "36",
                "optionID": "6"
            }
        ]
    }
    ],
    "count": 2
  }
}
```

---

### product

**URL:** `http://api.brain.com.ua/product/productID/SID[?lang=lang]`  
**HTTP Метод:** `GET`

**Опис:** Метод отримання інформації по зазначеному товару.

**Параметри:**

| Назва параметра | Обов'язковий | Опис |
|---|---|---|
| productID | так | ідентифікатор товару |
| SID | так | ідентифікатор сесії |
| lang | ні | мова: `ua`, `ru` або `ua_ru`; за замовч. `ua` |

> При `lang=ua_ru` поля `name`, `brief_description`, `description`, `country`, `options` повертаються українською, плюс додаткові поля `name_ru`, `brief_description_ru`, `description_ru`, `country_ru`, `options_ru` — російською.

**Приклад відповіді:**
```json
{
  "status": 1,
  "result": {
    "name": "Ноутбук Apple MacBook Pro",
    "brief_description": "короткий опис товара Apple MacBook Pro",
    "description": "повний опис товара Apple MacBook Pro",
    "country": "Китай",
    "productID": 12345,
    "categoryID": 1181,
    "product_code": "S1234567",
    "date_added": "2012-08-07 21:34:17",
    "date_modified": "2012-08-14 15:30:52",
    "actionID": 0,
    "warranty": "24",
    "is_archive": false,
    "is_exclusive": false,
    "vendorID": 123,
    "articul": "C13T06354A10",
    "volume": 0.02,
    "weight": 6,
    "kbt": 2,
    "is_price_cut": false,
    "is_new": false,
    "price": "1193.00",
    "price_uah": "10916.00",
    "recommendable_price": 11234.56,
    "retail_price_uah": "11256.00",
    "bonus": "5.00",
    "stocks": [1, 2, 3],
    "stocks_expected": {"4": "...", "6": "..."},
    "available": {"1": 3, "2": 1, "3": 1},
    "self_delivery": "1",
    "small_image": "https://opt.brain.com.ua/static/images/prod_img/6/7/S1234567_small.jpg",
    "medium_image": "https://opt.brain.com.ua/static/images/prod_img/6/7/S1234567.jpg",
    "large_image": "https://opt.brain.com.ua/static/images/prod_img/6/7/S1234567_big.jpg",
    "full_image": "https://opt.brain.com.ua/static/images/prod_img/6/7/S1234567_main.jpg",
    "quantity_package_sale": 0,
    "koduktved": "8517120000",
    "reservation_limit": 0,
    "non_returnable": 1,
    "options": [
      {"name": "Виробник", "value": "Apple", "optionID": "1"},
      {"name": "Модель", "value": "MacBook Pro", "optionID": "2"},
      {"name": "Розмір екрану", "value": "17.3\"TFT LED (1920x1200)", "optionID": "4", "valueID": "12345678900"},
      {"name": "Процесор", "value": "Intel Core i7 (2.4GHz, SLC 8Mb)", "optionID": "5", "valueID": "12345678901"},
      {"name": "Гарантія, міс", "value": "24", "optionID": "12"}
    ]
  }
}
```

---

### product/articul

**URL:** `http://api.brain.com.ua/product/articul/articul/SID[?lang=lang]`  
**HTTP Метод:** `GET`

**Опис:** Метод отримання інформації по зазначеному артикулу товару.

**Параметри:**

| Назва параметра | Обов'язковий | Опис |
|---|---|---|
| articul | так | артикул товару |
| SID | так | ідентифікатор сесії |
| lang | ні | мова: `ua`, `ru` або `ua_ru`; за замовч. `ua` |

> При `lang=ua_ru` повертаються ті самі додаткові поля, що і для методу `product`.

**Результат:** Метод повертає список параметрів за вказаним артикулом товару. Структура відповіді ідентична методу [product](#product).

**Приклад запиту:**
```
http://api.brain.com.ua/product/articul/C13T06354A10/gpkavk4s0aciujg6m698gev040
```

---

### product/product_code

**URL:** `http://api.brain.com.ua/product/product_code/product_code/SID[?lang=lang]`  
**HTTP Метод:** `GET`

**Опис:** Метод для отримання інформації по зазначеному коду товару.

**Параметри:**

| Назва параметра | Обов'язковий | Опис |
|---|---|---|
| product_code | так | код товару |
| SID | так | ідентифікатор сесії |
| lang | ні | мова: `ua`, `ru` або `ua_ru`; за замовч. `ua` |

**Результат:** Структура відповіді ідентична методу [product](#product).

**Приклад запиту:**
```
http://api.brain.com.ua/product/product_code/S1234567/gpkavk4s0aciujg6m698gev040
```

---

### categories

**URL:** `http://api.brain.com.ua/categories/SID[?lang=lang]`  
**HTTP Метод:** `GET`

**Опис:** Метод для отримання списку категорій товарів.

**Параметри:**

| Назва параметра | Обов'язковий | Опис |
|---|---|---|
| SID | так | ідентифікатор сесії |
| lang | ні | мова: `ua` або `ru`; за замовч. `ua` |

**Результат:** Список категорій з полями: `name`, `categoryID`, `parentID`, `realcat`.
- Якщо `parentID=1` — категорія верхнього рівня.
- Якщо `realcat > 0` — «віртуальна» категорія, що містить товари категорії з ідентифікатором `realcat`.

**Приклад відповіді:**
```json
{
  "status": 1,
  "result": [
    {"categoryID": 11, "parentID": 1, "realcat": 0, "name": "Комп'ютери"},
    {"categoryID": 12, "parentID": 11, "realcat": 0, "name": "Комплектуючі"},
    {"categoryID": 21, "parentID": 1, "realcat": 0, "name": "Ноутбуки"},
    {"categoryID": 22, "parentID": 21, "realcat": 14, "name": "Гаджети (Hi-Tech)"}
  ]
}
```

---

### vendors

**URL:** `http://api.brain.com.ua/vendors/[categoryID/]SID`  
**HTTP Метод:** `GET`

**Опис:** Метод для отримання списку виробників товарів [зазначеної категорії].

**Параметри:**

| Назва параметра | Обов'язковий | Опис |
|---|---|---|
| categoryID | ні | ідентифікатор категорії |
| SID | так | ідентифікатор сесії |

**Результат:**
- З `categoryID` — список виробників зазначеної категорії: `vendorID`, `name`.
- Без `categoryID` — список виробників усіх категорій: `vendorID`, `name`, `categoryID`.

**Приклад з категорією:**
```json
{
  "status": 1,
  "result": [
    {"vendorID": 11, "name": "ACER"},
    {"vendorID": 12, "name": "Apple"},
    {"vendorID": 13, "name": "ASUS"}
  ]
}
```

**Приклад без категорії:**
```json
{
  "status": 1,
  "result": [
    {"vendorID": 11, "name": "ACER", "categoryID": "125"},
    {"vendorID": 12, "name": "Apple", "categoryID": "125"},
    {"vendorID": 15, "name": "Samsung", "categoryID": "2345"}
  ]
}
```

---

### content

**URL:** `http://api.brain.com.ua/products/content/SID`  
**HTTP Метод:** `POST`

**Опис:** Метод отримання списку товарів з базовим контентом.

**Параметри URL:**

| Назва параметра | Обов'язковий | Опис |
|---|---|---|
| SID | так | ідентифікатор сесії |

**Параметри POST запиту:**

| Назва параметра | Обов'язковий | Опис |
|---|---|---|
| productIDs | так | рядок з ідентифікаторами товарів через кому |
| lang | ні | мова: `ua` або `ru`; за замовч. `ua` |

**Приклад запиту:**
```
POST http://api.brain.com.ua/products/content/gpkavk4s0aciujg6m698gev040
POST FIELDS:
productIDs: 1,2,3,4,5,6,....,12321
```

**Приклад відповіді:**
```json
{
  "status": 1,
  "result": {
    "list": [{
      "articul": "31730988100",
      "brief_description": "пластик, 2 x 2 Вт (RMS), чорний",
      "categoryID": 1038,
      "description": "Genius SP-U150 Black (31730988100) - компактна та стильна...",
      "name": "Акустична система Genius SP-U150 Black (31730988100)",
      "model": "SP-U150 Black",
      "productID": 101,
      "product_code": "U0000707",
      "vendorID": 1178,
      "volume": 0,
      "warranty": "12",
      "weight": 0.6,
      "kbt": 0,
      "date_added": "2012-08-07 21:33:58",
      "koduktved": "837843263",
      "country": "Китай",
      "options": [
        {
          "FilterID": "62-86000110400",
          "FilterName": "Системи 2.0",
          "OptionID": "62",
          "OptionName": "Клас товару",
          "ValueID": "86000110400",
          "ValueName": "Системи 2.0"
        }
      ],
      "images": [
        {
          "priority": 0,
          "small_image": "https://opt.brain.com.ua/static/images/prod_img/0/7/U0000707_small.jpg",
          "medium_image": "https://opt.brain.com.ua/static/images/prod_img/0/7/U0000707.jpg",
          "large_image": "https://opt.brain.com.ua/static/images/prod_img/0/7/U0000707_big.jpg",
          "full_image": "https://opt.brain.com.ua/static/images/prod_img/0/7/U0000707_main.jpg"
        }
      ]
    }]
  }
}
```

---

### modified_products

**URL:** `http://api.brain.com.ua/modified_products/type/SID[?modified_time=2016-04-17+07:00:00][&limit=1000][&offset=1000]`  
**HTTP Метод:** `GET`

**Опис:** Метод для отримання списку ідентифікаторів товарів, які були змінені.

**Параметри:**

| Назва параметра | Обов'язковий | Опис |
|---|---|---|
| type | ні | тип модифікації: `images`, `descriptions`, `options`, `new`; якщо порожньо — всі зміни |
| SID | так | ідентифікатор сесії |
| modified_time | ні | час останньої модифікації (за замовч. — доба). Формат: `2016-04-17 07:00:00` |
| limit | ні | кількість ID товару (за замовч. 1000, макс. 10 000, мін. 100) |
| offset | ні | усунення |

**Приклад відповіді:**
```json
{
  "status": 1,
  "result": {
    "productIDs": [12123, 123124, 123125],
    "count": 32133,
    "current": "2016-09-29 10:23:21"
  }
}
```

---

### product_options

**URL:** `http://api.brain.com.ua/product_options/productID/SID[?lang=lang]`  
**HTTP Метод:** `GET`

**Опис:** Метод отримання всіх характеристик товару.

**Параметри:**

| Назва параметра | Обов'язковий | Опис |
|---|---|---|
| productID | так | ідентифікатор товару |
| SID | так | ідентифікатор сесії |
| lang | ні | мова: `ua` або `ru`; за замовч. `ua` |

**Приклад відповіді:**
```json
{
  "status": 1,
  "result": [
    {
      "OptionID": "216",
      "OptionName": "Тип ноутбука",
      "ValueID": "86012946000",
      "ValueName": "Для роботи та навчання",
      "FilterID": "216-86012946000",
      "FilterName": "Для роботи та навчання"
    },
    {
      "OptionID": "6615",
      "OptionName": "Діагональ дисплея",
      "ValueID": "86012974500",
      "ValueName": "15.6\"",
      "FilterID": "6615-g2828",
      "FilterName": "15.6\" - 16\""
    },
    {
      "OptionID": "6617",
      "OptionName": "Поверхня екрану",
      "ValueID": "86012949800",
      "ValueName": "глянцева"
    }
  ]
}
```

---

### product_pictures

**URL:** `http://api.brain.com.ua/product_pictures/productID/SID`  
**HTTP Метод:** `GET`

**Опис:** Метод для отримання адрес картинок вказаного товару.

**Параметри:**

| Назва параметра | Обов'язковий | Опис |
|---|---|---|
| productID | так | ідентифікатор товару |
| SID | так | ідентифікатор сесії |

**Приклад відповіді:**
```json
{
  "status": 1,
  "result": [
    {
      "priority": 0,
      "small_image": "https://opt.brain.com.ua/static/images/prod_img/6/4/U0102664_small.jpg",
      "medium_image": "https://opt.brain.com.ua/static/images/prod_img/6/4/U0102664.jpg",
      "large_image": "https://opt.brain.com.ua/static/images/prod_img/6/4/U0102664_big.jpg",
      "full_image": "https://opt.brain.com.ua/static/images/prod_img/6/4/U0102664_main.jpg"
    },
    {
      "priority": 1,
      "small_image": "https://opt.brain.com.ua/static/images/prod_img/6/4/U0102664_2small.jpg",
      "medium_image": "https://opt.brain.com.ua/static/images/prod_img/6/4/U0102664_2.jpg",
      "large_image": "https://opt.brain.com.ua/static/images/prod_img/6/4/U0102664_2big.jpg",
      "full_image": "https://opt.brain.com.ua/static/images/prod_img/6/4/U0102664_2main.jpg"
    }
  ]
}
```

---

### products_pictures

**URL:** `http://api.brain.com.ua/products_pictures/categoryID/SID`  
**Необов'язкові параметри:** `[?vendorID=vendorID][&search=search][&filterID=filterID][&filters[]=filterID][&limit=limit][&offset=offset][&sortby=field_name][&order=order][&lang=lang]`  
**HTTP Метод:** `GET`

**Опис:** Метод для отримання адрес картинок товарів зазначеної категорії та всіх її дочірніх категорій.

**Параметри:** Ідентичні методу [products](#products).

**Приклад відповіді:**
```json
{
  "status": 1,
  "result": {
    "list": [
      {
        "productID": 101,
        "pictures": [
          {
            "priority": 0,
            "small_image": "https://opt.brain.com.ua/static/images/prod_img/6/7/S1234567_small.jpg",
            "medium_image": "https://opt.brain.com.ua/static/images/prod_img/6/7/S1234567.jpg",
            "large_image": "https://opt.brain.com.ua/static/images/prod_img/6/7/S1234567_big.jpg",
            "full_image": "https://opt.brain.com.ua/static/images/prod_img/6/7/S1234567_main.jpg"
          }
        ]
      }
    ]
  }
}
```

---

### comments

**URL:** `http://api.brain.com.ua/comments/productID/SID`  
**HTTP Метод:** `POST`

**Опис:** Метод для отримання коментарів (відгуків) до вказаного товару.

**Параметри:**

| Назва параметра | Обов'язковий | Опис |
|---|---|---|
| productID | так | ідентифікатор товару |
| SID | так | ідентифікатор сесії |

**Приклад відповіді:**
```json
{
  "status": 1,
  "result": {
    "list": [
      {"author": "Андрій", "body": "Чудовий товар", "add_time": "2012-08-14 18:34:29"},
      {"author": "Віктор", "body": "Дайте дві!", "add_time": "2012-08-17 15:00:17"}
    ],
    "count": 2
  }
}
```

---

### filters

**URL:** `http://api.brain.com.ua/filters/categoryID/SID[?lang=lang]`  
**HTTP Метод:** `GET`

**Опис:** Метод отримання списку базових фільтрів зазначеної категорії.

**Параметри:**

| Назва параметра | Обов'язковий | Опис |
|---|---|---|
| categoryID | так | ідентифікатор категорії |
| SID | так | ідентифікатор сесії |
| lang | ні | мова: `ua` або `ru`; за замовч. `ua` |

**Результат:** Список базових фільтрів з полями `filterID` і `name`.

**Приклад відповіді:**
```json
{
  "status": 1,
  "result": [
    {"filterID": "123-12345678901", "name": "Початкового рівня"},
    {"filterID": "123-12345678902", "name": "Мультимедійні"},
    {"filterID": "123-12345678903", "name": "Професійні"}
  ]
}
```

---

### filters_all

**URL:** `http://api.brain.com.ua/filters_all/categoryID/SID[?lang=lang]`  
**HTTP Метод:** `GET`

**Опис:** Метод отримання повного списку фільтрів зазначеної категорії, згрупованих за характеристиками товарів.

**Параметри:**

| Назва параметра | Обов'язковий | Опис |
|---|---|---|
| categoryID | так | ідентифікатор категорії |
| SID | так | ідентифікатор сесії |
| lang | ні | мова: `ua` або `ru`; за замовч. `ua` |

**Приклад відповіді:**
```json
{
  "status": 1,
  "result": [
    {
      "name": "Тип ноутбука",
      "optionID": 216,
      "filters": [
        {"filterID": "216-86012946200", "name": "Apple"},
        {"filterID": "216-86012946000", "name": "Для роботи та навчання"},
        {"filterID": "216-86012945300", "name": "Ігровий"}
      ]
    },
    {
      "name": "Виробник",
      "optionID": 3,
      "filters": [
        {"filterID": "3-75001200000", "name": "Acer"},
        {"filterID": "3-83017200000", "name": "Apple"},
        {"filterID": "3-02303000000", "name": "ASUS"}
      ]
    },
    {
      "name": "Діагональ екрану",
      "optionID": 6615,
      "filters": [
        {"filterID": "6615-g2830", "name": "10.1\" - 12.5\""},
        {"filterID": "6615-g2829", "name": "13.3\" - 14.1\""},
        {"filterID": "6615-g2828", "name": "15.6\" - 16\""},
        {"filterID": "6615-g2827", "name": "17.3\" - 18.4\""}
      ]
    }
  ]
}
```

---

## 3. Доступність товарів

### delivery_time

**URL:** `http://api.brain.com.ua/delivery_time/productID/stockIDs/SID`  
**HTTP Метод:** `GET`

**Опис:** Метод отримання часу доступності зазначеного товару на вказаних складах.

**Параметри:**

| Назва параметра | Обов'язковий | Опис |
|---|---|---|
| productID | так | ідентифікатор товару |
| stockIDs | так | ідентифікатори складів (один або кілька через кому) |
| SID | так | ідентифікатор сесії |

**Результат:** Час доступності у форматі UNIX timestamp.

**Приклади:**
```
# Один склад
http://api.brain.com.ua/delivery_time/355/25/SID
→ {"status":1,"result":1347284391}

# Кілька складів
http://api.brain.com.ua/delivery_time/355/1,58,34/SID
→ {"status":1,"result":[{"stockID":1,"time":138785020},{"stockID":58,"time":138785020},{"stockID":34,"time":138785020}]}
```

---

### delivery_time/product_code

**URL:** `http://api.brain.com.ua/delivery_time/product_code/product_code/stockIDs/SID`  
**HTTP Метод:** `GET`

**Опис:** Метод для отримання часу доступності вказаного товару на вказаних складах за кодом товару.

**Параметри:**

| Назва параметра | Обов'язковий | Опис |
|---|---|---|
| product_code | так | код товару |
| stockIDs | так | ідентифікатори складів (один або кілька через кому) |
| SID | так | ідентифікатор сесії |

**Приклади:**
```
# Один склад
http://api.brain.com.ua/delivery_time/product_code/U1234567/25/SID
→ {"status":1,"result":1347284391}

# Кілька складів
http://api.brain.com.ua/delivery_time/product_code/U1234567/1,58,34/SID
→ {"status":1,"result":[{"stockID":1,"time":138785020},{"stockID":58,"time":138785020},{"stockID":34,"time":138785020}]}
```

---

### targets

**URL:** `http://api.brain.com.ua/targets/SID`  
**HTTP Метод:** `GET`

**Опис:** Метод для отримання списку пунктів видачі / служб доставки.

**Параметри:**

| Назва параметра | Обов'язковий | Опис |
|---|---|---|
| SID | так | ідентифікатор сесії |

**Результат:** Список з полями: `targetID`, `name`, `type`, `weightlimit`, `volumelimit`, `region`.

**Приклад відповіді:**
```json
{
  "status": 1,
  "result": [
    {
      "targetID": "1",
      "name": "ПВ Дніпро, вул.Миру 1а",
      "type": "Самовывоз",
      "weightlimit": "40.00",
      "volumelimit": "0.00000",
      "region": "Дніпро"
    },
    {
      "targetID": "4",
      "name": "Відправка Новою поштою",
      "type": "Служба доставки",
      "weightlimit": "30.00",
      "volumelimit": "0.00000",
      "region": "Київ"
    }
  ]
}
```

---

### discounted_targets

**URL:** `http://api.brain.com.ua/discounted_targets/SID`  
**HTTP Метод:** `GET`

**Опис:** Метод для отримання списку пунктів видачі знижених у ціні товарів.

**Параметри:**

| Назва параметра | Обов'язковий | Опис |
|---|---|---|
| SID | так | ідентифікатор сесії |

**Приклад відповіді:**
```json
{
  "status": 1,
  "result": [
    {"targetID": 1, "name": "Київ_УТ_Перемоги 67"},
    {"targetID": 2, "name": "Київ_Нивки_УТ"},
    {"targetID": 7, "name": "Харків УТ"}
  ]
}
```

---

### addresses

**URL:** `http://api.brain.com.ua/addresses/SID`  
**HTTP Метод:** `GET`

**Опис:** Метод для отримання списку адрес доставки.

**Параметри:**

| Назва параметра | Обов'язковий | Опис |
|---|---|---|
| SID | так | ідентифікатор сесії |

**Результат:** Список з полями: `addressID`, `name`, `address`, `targets` (ідентифікатори служб, що можуть здійснити доставку).

**Приклад відповіді:**
```json
{
  "status": 1,
  "result": [
    {"addressID": 128, "name": "Адреса доставки 1", "address": "Київ, вул.Володимирська, буд.10, кв.12", "targets": "3,4,5"},
    {"addressID": 134, "name": "Адреса доставки 2", "address": "Дніпро, вул.Вокзальна, буд.56, кв.3", "targets": "3,4"}
  ]
}
```

---

### stocks

**URL:** `http://api.brain.com.ua/stocks/SID`  
**HTTP Метод:** `GET`

**Опис:** Метод для отримання списку складів.

**Параметри:**

| Назва параметра | Обов'язковий | Опис |
|---|---|---|
| SID | так | ідентифікатор сесії |

**Приклад відповіді:**
```json
{
  "status": 1,
  "result": [
    {"stockID": 1, "name": "Київ Головний"},
    {"stockID": 2, "name": "Київ Нивки"},
    {"stockID": 3, "name": "Київ Лівобережний"},
    {"stockID": 4, "name": "Харків Головний"},
    {"stockID": 5, "name": "Одеса Головний"},
    {"stockID": 6, "name": "Львів Головний"}
  ]
}
```

---

## 4. Робота із замовленнями

### GET order

**URL:** `http://api.brain.com.ua/order/SID`  
**HTTP Метод:** `GET`

**Опис:** Метод для отримання списку товарів із кошика.

**Параметри:**

| Назва параметра | Обов'язковий | Опис |
|---|---|---|
| SID | так | ідентифікатор сесії |

> `"price": "0.00"` та `"price_uah": "0.00"` — заборона купівлі цієї групи товарів; зверніться до менеджера.

**Приклад відповіді:**
```json
{
  "status": 1,
  "result": [
    {
      "productID": "650",
      "product_code": "U0001831",
      "articul": "NU.SGAEU.006",
      "quantity": "3",
      "comment": "",
      "price": "250.15",
      "price_uah": "2226.34"
    },
    {
      "productID": "833",
      "product_code": "B0000988",
      "articul": "GT-P1000CWA",
      "quantity": "5",
      "comment": "some comment",
      "price": "340.28",
      "price_uah": "3028.49"
    }
  ]
}
```

---

### POST order

**URL:** `http://api.brain.com.ua/order/SID`  
**HTTP Метод:** `POST`

**Опис:** Метод додавання товарів у кошик. Якщо товар вже присутній — оновлюється.

**Параметри URL:**

| Назва параметра | Обов'язковий | Опис |
|---|---|---|
| SID | так | ідентифікатор сесії |

**Параметри POST запиту:**

| Назва параметра | Обов'язковий | Опис |
|---|---|---|
| data | так | JSON рядок зі списком товарів |
| recipient_type | ні (так — для комісійного продажу) | тип кінцевого клієнта: `0` — фіз. особа, `1` — юр. особа; за замовч. `0` |

**Параметри об'єктів у JSON:**

| Назва параметра | Обов'язковий | Опис |
|---|---|---|
| productID | ні (якщо вказано product_code або articul) | ID товару |
| product_code | ні (якщо вказано productID або articul) | код товару |
| articul | ні (якщо вказано productID або product_code) | артикул товару |
| quantity | так | кількість одиниць |
| recipient_price | ні (так — для комісійного продажу) | ціна товару для рахунку |
| comment | ні | коментар до товару |

> Обов'язково має бути вказаний хоча б один з: `productID`, `product_code`, `articul`.

**Приклад JSON:**
```json
[
  {"productID": "15949", "quantity": "12", "recipient_price": "1299.00", "comment": "thank for service"},
  {"product_code": "B0015377", "quantity": "1", "recipient_price": "513.00"}
]
```

**Приклад PHP (CURL):**
```php
$data = json_encode(array(
    array('productID' => '15949', 'quantity' => '12', 'recipient_price' => '1299.00', 'comment' => 'thank for service'),
    array('product_code' => 'B0015377', 'quantity' => '1', 'recipient_price' => '513.00')
));
$ch = curl_init();
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_POST, 1);
curl_setopt($ch, CURLOPT_POSTFIELDS, array('data' => $data));
curl_setopt($ch, CURLOPT_URL, $url);
$result = curl_exec($ch);
```

**Приклад відповіді:**
```json
{"status":"1","result":"1"}
```

---

### POST order/delete

**URL:** `http://api.brain.com.ua/order/delete/SID`  
**HTTP Метод:** `POST`

**Опис:** Метод видалення товарів з поточного замовлення.

**Параметри URL:**

| Назва параметра | Обов'язковий | Опис |
|---|---|---|
| SID | так | ідентифікатор сесії |

**Параметри POST запиту:**

| Назва параметра | Обов'язковий | Опис |
|---|---|---|
| data | так | JSON рядок зі списком товарів для видалення |

**Параметри об'єктів у JSON:**

| Назва параметра | Обов'язковий | Опис |
|---|---|---|
| productID | ні (якщо вказано product_code) | ID товару для видалення |
| product_code | ні (якщо вказано productID) | код товару для видалення |

**Приклад:**
```json
[{"productID": "15949"}, {"product_code": "B0015377"}]
```

**Приклад відповіді:**
```json
{"status":"1","result":"1"}
```

---

### clear_cart

**URL:** `http://api.brain.com.ua/clear_cart/SID`  
**HTTP Метод:** `GET`

**Опис:** Метод для очищення корзини.

**Параметри:**

| Назва параметра | Обов'язковий | Опис |
|---|---|---|
| SID | так | ідентифікатор сесії |

**Приклад відповіді:**
```json
{"status": 1}
```

---

### put_order

**URL:** `http://api.brain.com.ua/order/put/SID`  
**HTTP Метод:** `POST`

**Опис:** Метод для оформлення поточного замовлення (створення замовлення із кошика).

**Параметри URL:**

| Назва параметра | Обов'язковий | Опис |
|---|---|---|
| SID | так | ідентифікатор сесії |

**Параметри POST запиту:**

| Назва параметра | Обов'язковий | Опис |
|---|---|---|
| currency | так | валюта: `USD` або `UAH` |
| targetID | так | ідентифікатор пункту видачі / служби доставки |
| addressID | ні | ідентифікатор адреси доставки |
| contactID | ні | ідентифікатор контактної особи |
| clientID | ні | ідентифікатор клієнта |
| comment | ні | коментар до замовлення |

**Приклад відповіді:**
```json
{
  "status": 1,
  "result": {
    "orderID": 999999
  }
}
```

---

### reserve_order

**URL:** `http://api.brain.com.ua/order/orderID/reserve/SID`  
**HTTP Метод:** `POST`

**Опис:** Метод бронювання замовлення.

**Параметри URL:**

| Назва параметра | Обов'язковий | Опис |
|---|---|---|
| orderID | так | ідентифікатор замовлення |
| SID | так | ідентифікатор сесії |

**Параметри POST запиту:**

| Назва параметра | Обов'язковий | Опис |
|---|---|---|
| reserveddate | ні | дата бронювання (за замовч. +1 доба); формат: `DD.MM.YYYY` |
| clientID | ні | ідентифікатор клієнта |

> Якщо у замовленні є товари з `reservation_limit > 0`, дата бронювання = поточна дата незалежно від `reserveddate`.

**Приклад відповіді:**
```json
{"status": 1, "reserveddate": "02.07.2026"}
```

---

### ship_order

**URL:** `http://api.brain.com.ua/order/orderID/ship/SID`  
**HTTP Метод:** `POST`

**Опис:** Метод для відвантаження замовлення.

**Параметри URL:**

| Назва параметра | Обов'язковий | Опис |
|---|---|---|
| orderID | так | ідентифікатор замовлення |
| SID | так | ідентифікатор сесії |

**Параметри POST запиту:**

| Назва параметра | Обов'язковий | Опис |
|---|---|---|
| shipingdate | ні | дата та час відвантаження; формат: `DD.MM.YYYY HH:ii` |
| subsidiaryID | ні | ідентифікатор філії компанії |
| accounting | ні | необхідність бухобліку: `1` — так, `0` — ні |
| clientID | ні | ідентифікатор клієнта |

**Приклад відповіді:**
```json
{"status": 1}
```

---

### close_order

**URL:** `http://api.brain.com.ua/order/orderID/close/SID`  
**HTTP Метод:** `POST`

**Опис:** Метод закриття замовлення.

**Параметри URL:**

| Назва параметра | Обов'язковий | Опис |
|---|---|---|
| orderID | так | ідентифікатор замовлення |
| SID | так | ідентифікатор сесії |

**Приклад відповіді:**
```json
{"status": "1"}
```

---

### orders

**URL:** `http://api.brain.com.ua/orders/SID`  
**Необов'язкові параметри:** `[?type=type][&ordererID=ordererID][&date_start=date_start][&date_finish=date_finish][&limit=limit][&offset=offset][&lang=lang]`  
**HTTP Метод:** `GET`

**Опис:** Метод отримання списку замовлень.

**Параметри:**

| Назва параметра | Обов'язковий | Опис |
|---|---|---|
| SID | так | ідентифікатор сесії |
| type | ні | тип замовлення (див. таблицю нижче) |
| ordererID | ні | ідентифікатор замовника |
| orderID | ні | ідентифікатор замовлення |
| date_start | ні | початкова дата; формат: `DD.MM.YYYY` |
| date_finish | ні | кінцева дата; формат: `DD.MM.YYYY` |
| limit | ні | кількість замовлень (макс. 100) |
| offset | ні | кількість замовлень, що пропускаються; за замовч. 0 |
| lang | ні | мова: `ua` або `ru`; за замовч. `ua` |

> Якщо передана лише одна дата — використовується діапазон за замовчуванням (перше число поточного місяця — поточна дата).

**Типи замовлень:**

| Тип | Опис |
|---|---|
| new | Чернетка |
| invoice | Рахунок |
| quotation | Рахунок |
| reserved | Бронь |
| ordered | Відвантаження |
| preordered | Попереднє замовлення |
| prepaid | Відвантаження по передоплаті |

> `"delivery_time": "blocked"` — заборона купівлі цієї групи товарів; зверніться до менеджера.  
> `count` — кількість замовлень без урахування `offset` та `limit`.

**Приклад відповіді:**
```json
{
  "status": 1,
  "result": {
    "list": [
      {
        "orderID": "297487",
        "ordererID": "1",
        "type": "Відвантаження",
        "status": "Обробка",
        "currency": "USD",
        "quantity": 5,
        "amount": 259.77,
        "actual_amount": 259.77,
        "volume": 0.35,
        "delivery_type": "home",
        "addressID": "0",
        "subsidiaryID": null,
        "targetID": "65",
        "reserveddate": "25.12.2013",
        "reservedquantity": 0,
        "shipingdate": "30.12.2013 13:03",
        "accounting": "0",
        "closed": null,
        "clientID": null,
        "add_time": "2013-12-18 17:19:44",
        "update_time": "2013-12-24 10:32:31",
        "items": [
          {"productID": "1155", "quantity": "2", "price": "38.01", "actual_price": "38.01", "invoice_price": "0.00", "delivery_time": "30.12.2013 13:03", "reservedquantity": "0"}
        ],
        "comments": [
          {"publication_time": "2013-12-24 10:32:31", "author": "Веб-автомат", "text": "Враховано вартість доставки 200.00 грн"}
        ]
      }
    ],
    "count": 2
  }
}
```

---

## 5. Механізм комісійного продажу

### add_recipient

**URL:** `http://api.brain.com.ua/add_recipient/SID`  
**HTTP Метод:** `POST`

**Опис:** Метод для створення кінцевого клієнта та адреси доставки. Використовується як для комісійного продажу, так і для дропшипінгу.

**Параметри URL:**

| Назва параметра | Обов'язковий | Опис |
|---|---|---|
| SID | так | ідентифікатор сесії |

**Параметри POST запиту:**

| Назва параметра | Обов'язковий | Опис |
|---|---|---|
| recipient_type | так | тип клієнта: `1` — юрособа, `0` — фізособа |
| name | так | ПІБ одержувача |
| legal_name | так (для юросіб) | юр. назва одержувача |
| okpo | так (для юросіб) | код ЄДРПОУ |
| vat_code | так (для юросіб — платників ПДВ) | код ІПН |
| non_payer_vat | ні (так — якщо не вказано ІПН) | не платник ПДВ: `0` — ні, `1` — так; для юр. осіб |
| legal_address | ні | юр. адреса |
| legal_phone | ні | телефон юр. особи у форматі `0000000000` |
| phone_number | так | телефон одержувача у форматі `0000000000` |
| email | ні | електронна пошта |
| delivery_type | так | варіант отримання: `self` — склад, `home` — двері |
| delivery_service_code | так | код служби доставки |
| targetID | так (для `self`) | ідентифікатор ПВ |
| cityID | так (для `home`) | ідентифікатор міста |
| streetID | так (для `home`) | ідентифікатор вулиці |
| building | так (для `home`) | номер будинку |
| flat | ні | номер квартири |
| floor | ні | поверх (тільки для Нової Пошти) |
| lift | ні | наявність ліфта: `0` — немає, `1` — є (тільки для Нової Пошти) |
| comment | ні | коментар для поштової декларації |

**Приклад відповіді:**
```json
{
  "status": 1,
  "recipientID": 23,
  "addressID": 456
}
```

---

### ship_order_to_recipient

**URL:** `http://api.brain.com.ua/order/orderID/ship_to_recipient/SID`  
**HTTP Метод:** `POST`

**Опис:** Метод для відвантаження замовлення кінцевому клієнту (комісійний продаж).

**Параметри URL:**

| Назва параметра | Обов'язковий | Опис |
|---|---|---|
| orderID | так | ідентифікатор замовлення |
| SID | так | ідентифікатор сесії |

**Параметри POST запиту:**

| Назва параметра | Обов'язковий | Опис |
|---|---|---|
| recipientID | так | ідентифікатор одержувача |
| addressID | так | ідентифікатор адреси одержувача |
| delivery_cost | ні | вартість доставки, грн |
| recipient_order_number | ні | номер замовлення в обліковій системі Партнера |
| recipient_order_date | ні | дата замовлення в обліковій системі Партнера; формат: `DD.MM.YYYY` |
| shiping_date | ні | дата доставки кур'єром; формат: `DD.MM.YYYY` |
| delivery_period | ні | період доставки кур'єром (пн-пт: 1 — 10:00-15:00, 2 — 15:00-19:00; сб: 3 — 11:00-17:00; КБТ пн-пт: 4 — 11:00-17:00) |
| courier_terminal | ні | оплата банківською картою (тільки для кур'єра): `0` — ні, `1` — так |
| payment_method_type | ні | ІД виду оплати: `1` — безготівково, `5` — післяплата готівкою |
| payer_delivery | ні | платник за доставку: `0` — дилер, `1` — одержувач; за замовч. `0` |

**Приклад відповіді:**
```json
{"status": 1}
```

---

## 6. Дропшипінг

> Для дропшипінгу спочатку використовується метод [add_recipient](#add_recipient) для створення клієнта, потім — метод нижче.

### ship_order_to_drop

**URL:** `http://api.brain.com.ua/order/orderID/ship_to_drop/SID`  
**HTTP Метод:** `POST`

**Опис:** Метод для відвантаження замовлення по дропшипінгу.

**Параметри URL:**

| Назва параметра | Обов'язковий | Опис |
|---|---|---|
| orderID | так | ідентифікатор замовлення |
| SID | так | ідентифікатор сесії |

**Параметри POST запиту:**

| Назва параметра | Обов'язковий | Опис |
|---|---|---|
| recipientID | так | ідентифікатор одержувача |
| addressID | так | ідентифікатор адреси одержувача |
| payer_delivery | ні | платник за доставку: `0` — дилер, `1` — одержувач; за замовч. `1` |
| delivery_cost | ні | вартість доставки, грн |
| recipient_order_number | ні | номер замовлення в обліковій системі Партнера |
| recipient_order_date | ні | дата замовлення; формат: `DD.MM.YYYY` |
| payment_method_type | ні | ІД виду оплати: `1` — безготівково, `5` — післяплата готівкою |
| min_insurance_amount | ні | мінімальна вартість страховки |

**Приклад відповіді:**
```json
{"status": 1}
```

---

## 7. Звіти

### report

**URL:** `http://api.brain.com.ua/report/report_type/SID[?date_from=DD.MM.YYYY&date_to=DD.MM.YYYY&file_type=html|xls&orderID=orderID]`  
**HTTP Метод:** `GET`

**Опис:** Метод для отримання звітів.

**Параметри:**

| Назва параметра | Обов'язковий | Опис |
|---|---|---|
| report_type | так | тип звіту (див. таблицю нижче) |
| SID | так | ідентифікатор сесії |
| date_from | ні | початкова дата; формат: `DD.MM.YYYY` |
| date_to | ні | кінцева дата; формат: `DD.MM.YYYY` |
| file_type | ні | формат: `html` або `xls`; за замовч. `html` |
| orderID | ні (обов'язково для `get_order_status`) | ідентифікатор замовлення |

> Якщо передана лише одна дата — використовується діапазон 14 днів до поточної дати.  
> Максимально можливий діапазон: **92 дні**.  
> Обмеження частоти: **не частіше 1 запиту в 300 секунд** для кожного типу; при перевищенні — помилка 54.

**Типи звітів:**

| Тип звіту | Назва |
|---|---|
| reserves | Звіт з резервів |
| payment_shedule | Платіжний календар |
| shipment_balance | Залишки по відвантаженням (повний) |
| shipment_balance_commission | Залишки з відвантажень (комісія) |
| client_card | Картка клієнта |
| client_card_commission | Картка клієнта (комісія) |
| warranty_list | Гарантійна відомість |
| warranty_list_commission | Гарантійна відомість (комісія) |
| b2bsales | В2В продажі |
| shipment_balance_short | Залишки по відвантаженням (короткий) |
| rejects_report | Звіт по браку товару |
| rejects_report_commission | Звіт по браку (комісія) |
| rejects_movements | Звіт з руху браку |
| bonuses | Бонуси |
| postal_declarations | Поштові декларації |
| get_order_status | Статус замовлення (orderID обов'язковий) |
| payments | Звіт з безготівки |
| payments_commission | Звіт з безготівки (комісія) |
| commission_sales | Комісійні продажі (повний) |
| commission_sales_processing | Комісійні продажі (у роботі) |
| order_report_logistics | Звіт по замовленнях (логістика) |
| com_returns | Незакриті повернення (комісія) |
| unclosed_com_docs | Незакриті документи (комісія) |
| serial_numbers_by_dealer | Серійні номери |
| lenovo_sales | Продажі Lenovo |

**Приклад відповіді (html):**
```json
{
  "status": 1,
  "result": "<p>Звіт у форматі html</p>"
}
```

**Приклад (xls):** повертає XLS файл.

---

## 8. Прайс-листи

### pricelists

**URL:** `http://api.brain.com.ua/pricelists/targetID/format/SID[?lang=lang][&full=full]`  
**HTTP Метод:** `GET`

**Опис:** Метод для отримання посилання на прайслист.

**Параметри:**

| Назва параметра | Обов'язковий | Опис |
|---|---|---|
| targetID | так | ідентифікатор пункту видачі |
| format | так | формат: `xml`, `xlsx`, `xls`, `json`, `php` |
| SID | так | ідентифікатор сесії |
| lang | ні | мова: `ua` або `ru`; за замовч. `ua` |
| full | ні | наявність: `0` — тільки локальний склад (повний прайс); `1` — вся наявність (повний прайс); `2` — вся наявність (короткий прайс); за замовч. `0` |

**Приклад відповіді:**
```json
{
  "status": 1,
  "url": "http://5.45.123.74/index.php?time=1406098966&companyID=1&targetID=29&format=xml&lang=ua&token=...&full=1"
}
```

---

### discounted_pricelists

**URL:** `http://api.brain.com.ua/discounted_pricelists/targetID/format/SID[?lang=lang]`  
**HTTP Метод:** `GET`

**Опис:** Метод для отримання посилання на прайслист знижених у ціні товарів.

**Параметри:**

| Назва параметра | Обов'язковий | Опис |
|---|---|---|
| targetID | так | ідентифікатор пункту видачі знижених товарів |
| format | так | формат: `xml`, `xlsx`, `xls`, `json`, `php` |
| SID | так | ідентифікатор сесії |
| lang | ні | мова: `ua` або `ru`; за замовч. `ua` |
| full | ні | наявність: `0` — тільки локальний склад; `1` — вся наявність (повний); `2` — вся наявність (короткий); за замовч. `0` |

**Приклад відповіді:**
```json
{
  "status": 1,
  "url": "http://5.45.123.74/discounted_price.php?time=1406098966&companyID=1&targetID=529&format=xml&lang=ua&token=...&full=1"
}
```

---

## 9. Додатково

### currencies

**URL:** `http://api.brain.com.ua/currencies/SID`  
**HTTP Метод:** `GET`

**Опис:** Метод для отримання списку та курсів валют.

**Параметри:**

| Назва параметра | Обов'язковий | Опис |
|---|---|---|
| SID | так | ідентифікатор сесії |

**Приклад відповіді:**
```json
{
  "status": 1,
  "result": [
    {"currencyID": 1, "name": "грн б/н", "value": "9"},
    {"currencyID": 2, "name": "грн нал", "value": "8.1"},
    {"currencyID": 3, "name": "грн DDP", "value": "8.1"}
  ]
}
```

---

### contacts

**URL:** `http://api.brain.com.ua/contacts/SID`  
**HTTP Метод:** `GET`

**Опис:** Метод для отримання списку контактних осіб.

**Параметри:**

| Назва параметра | Обов'язковий | Опис |
|---|---|---|
| SID | так | ідентифікатор сесії |

**Приклад відповіді:**
```json
{
  "status": 1,
  "result": [
    {"contactID": 15, "fullname": "Іваненко Іван Іванович", "position": "Начальник"},
    {"contactID": 128, "fullname": "Петренко Петро Петрович", "position": "Заступник начальника"}
  ]
}
```

---

## 10. Термінологія

| Концепція | Опис | Приклад |
|---|---|---|
| SID | Ідентифікатор сесії. Повертається методом `auth`. Обов'язковий для всіх запитів. | `jf234f823j4fhi7` |
| vendor (вендор) | Компанія, що надає товар. | Asus |
| vendorID | Унікальний ідентифікатор вендора. | `321` |
| category (категорія) | Характеристика продукту, що визначає його належність до певної групи товарів. | Ноутбуки |
| categoryID | Унікальний ідентифікатор категорії. | `162` |
| product (продукт) | Товар виставлений або запланований на продаж. | Ноутбук ASUS G53SX |
| productID | Унікальний ідентифікатор товару. | `233` |
| filter (фільтр) | Фільтр є унікальним для кожної категорії. | Ультрабуки |
| filterID | Унікальний ідентифікатор фільтру. | `123-12345678900` |
| stock (склад) | Назва складу. | Київ Нивки |
| stockID | Унікальний ідентифікатор складу. | `12` |
| currencyID | Унікальний ідентифікатор валюти. | `2` |
| targetID | Унікальний ідентифікатор пункту видачі / служби доставки. | `58` |
| addressID | Унікальний ідентифікатор адреси доставки. | `134` |
| contactID | Унікальний ідентифікатор контактної особи. | `1594` |
| JSON | Текстовий формат обміну даними на базі JavaScript. | `{"status": 1, "result": "Ok"}` |

---

## 11. Помилки та коди помилок

Якщо помилок немає — відповідь містить `"status": 1`.  
Якщо виникла помилка — `"status": 0` з кодом і описом:

```json
{"status": 0, "error_code": 21, "error_message": "No category with specified categoryID"}
```

**Таблиця кодів помилок:**

| Код | Повідомлення | Переклад |
|---|---|---|
| 1 | Login is required parameter | Не вказано логін |
| 2 | Password is required parameter | Не вказано пароль |
| 3 | Session identifier is required parameter | Не вказано SID |
| 4 | Session identifier is fault | Неправильний SID |
| 5 | Session identifier is outdate | Термін сесії закінчився |
| 6 | Incorrect login or password | Неправильний логін або пароль |
| 7 | User was blocked | Користувач заблокований |
| 8 | Incorrect categoryID | Неправильний categoryID |
| 9 | Incorrect filterID | Неправильний filterID |
| 10 | Incorrect limit | Неправильне значення limit |
| 11 | Incorrect max_price | Неправильне значення max_price |
| 12 | Incorrect min_price | Неправильне значення min_price |
| 13 | Incorrect offset | Неправильне значення offset |
| 14 | Incorrect order | Неправильне значення order |
| 15 | Incorrect productID | Неправильний productID |
| 16 | Incorrect search string | Неправильний рядок пошуку |
| 17 | Incorrect sortby | Неправильне значення sortby |
| 18 | Incorrect stockIDs | Неправильний stockIDs |
| 19 | Incorrect vendorID | Неправильний vendorID |
| 20 | Exceed max limit value | Перевищено максимальне значення limit |
| 21 | No category with specified categoryID | Категорію не знайдено |
| 22 | No delivery_time for specified productID and stockIDs | Немає часу отримання товару на складі |
| 23 | No product with specified productID | Товару не знайдено |
| 24 | No specified filter in specified category | Фільтр відсутній у категорії |
| 25 | No specified vendor in specified category | Виробника немає у категорії |
| 26 | No stock with specified stockIDs | Склад не знайдено |
| 27 | JSON format error | Неправильний формат JSON |
| 28 | Absent required parameters in product line | Немає обов'язкових параметрів товару |
| 29 | Invalid product parameters | Неправильні параметри товару |
| 30 | No data specified | Не вказані дані |
| 31 | Incorrect product | Неправильні параметри товару |
| 32 | Incorrect product code | Неправильний product_code |
| 33 | Incorrect articul | Неправильний артикул |
| 34 | Not enough permissions. Connect to administrator. | Недостатньо прав |
| 35 | Invalid date | Невірна дата |
| 36 | Exceeded max days range | Перевищено максимальний часовий діапазон |
| 37 | Failed to load data | Неможливо завантажити дані |
| 38 | Currency is required parameter | Не вказано валюту |
| 39 | Incorrect currency | Неправильна валюта |
| 40 | TargetID is required parameter | Не вказано targetID |
| 41 | Incorrect targetID | Неправильний targetID |
| 42 | AddressID is required for this shiping type | Потрібна адреса доставки |
| 43 | Incorrect addressID | Неправильний addressID |
| 44 | Incorrect binding address with target | Неправильна прив'язка адреси до служби |
| 45 | Error occurred. Please, contact administrator | Виникла помилка |
| 46 | No products list | Відсутній перелік товарів |
| 47 | Order not found | Замовлення не знайдено |
| 48 | Unaccessible operation | Операція недоступна |
| 49 | Shipingdate is required parameter | Дата відвантаження не вказана |
| 50 | Invalid shipingdate | Неправильна дата відвантаження |
| 51 | Incorrect subsidiaryID | Неправильний ідентифікатор відділення |
| 52 | Incorrect order type | Неправильний тип замовлення |
| 53 | No product with specified parameters | Товару із заданими параметрами немає |
| 54 | Exceeded the requests frequency for this type of report | Перевищення норми запитів для типу звітів |
| 55 | Incorrect contactID | Неправильний contactID |
| 56 | Invalid city or operator code | Неправильний код міста або оператора |
| 57 | Allowable phone symbols | Неприпустимі символи в номері телефону |
| 58 | Incorrect email phone or password | Неправильна email, телефон або пароль |
| 59 | Incorrect language | Неправильний мовний параметр |
| 60 | Incorrect pricelist format | Неправильний формат прайс-листа |
| 61 | Incorrect report format | Неправильний тип звіту |
| 62 | Incorrect type | Неприпустимий тип |
| 63 | Incorrect limit. It can not be less then 100 | Ліміт не може бути менше 100 |
| 64 | Incorrect modified time | Неправильний час модифікації |
| 65 | No delivery_time for specified products and target | Немає часу наявності товару в пункті |
| 66 | Incorrect orderID | Неправильний orderID |
| 67 | Incorrect recipientprice | Неправильна ціна для кінцевого споживача |
| 68 | Incorrect delivery service code | Неправильний код служби доставки |
| 69 | Incorrect targetID for specified delivery service | Неправильний targetID для служби доставки |
| 70 | Incorrect cityID for specified delivery service | Неправильний cityID для служби доставки |
| 71 | Incorrect streetID for specified delivery service | Неправильний streetID для служби доставки |
| 72 | Exceed max products limit | Перевищено максимальну кількість товарів |
| 73 | Recipient type is required parameter | Не вказано тип клієнта |
| 74 | Incorrect recipient type | Неправильний тип клієнта |
| 75 | Fullname is required parameter | ПІБ не вказано |
| 76 | Phone number is required parameter | Номер телефону не вказано |
| 77 | Delivery type is required parameter | Не вказано варіант отримання |
| 78 | Incorrect delivery type | Неправильний варіант отримання |
| 79 | Delivery service code is required parameter | Код служби доставки не вказано |
| 80 | Legalname is required parameter | Юридична назва не вказана |
| 81 | Okpo is required parameter | Код ЄДРПОУ не вказано |
| 82 | Invalid email | Неправильна email |
| 83 | CityID is required parameter | Не вказано cityID |
| 84 | StreetID is required parameter | Не вказано streetID |
| 85 | Building is required parameter | Будинок не вказано |
| 86 | Flat is required parameter | Квартира не вказана |
| 87 | The order doesnt match the parameters of target | Замовлення не відповідає параметрам ПВ |
| 88 | RecipientID is required parameter | Не вказано recipientID |
| 89 | Recipient not found | Клієнта не знайдено |
| 90 | AddressID is required parameter | Не вказано addressID |
| 91 | Address not found | Адресу доставки не знайдено |
| 92 | Delivery payer is required parameter | Не вказано платника доставки |
| 93 | Incorrect delivery payer | Неправильний платник доставки |
| 94 | Incorrect delivery cost | Неправильна вартість доставки |
| 95 | Incorrect streetID for specified city | Неправильний streetID для вказаного міста |
| 96 | Incorrect targetID for pricelist | Неправильний targetID для прайс-листа |
| 97 | Incorrect floor | Неправильний поверх |
| 98 | Incorrect ignore_restriction format | Неправильний формат ignore_restriction |
| 99 | Incorrect okpo | Неправильна ЄДРПОУ |
| 100 | Vatcode for payervat is required parameter | Не вказано ІПН (обов'язково для платника ПДВ) |
| 101 | Incorrect vatcode | Неправильний ІПН |
| 102 | Vatcode for nonpayervat is unavailable | ІПН для неплатника ПДВ відсутній |
| 103 | Floor is forbidden for specified delivery service | Поверх заборонений для служби доставки |
| 104 | Lift is forbidden for specified delivery service | Ліфт заборонений для служби доставки |
| 105 | Incorrect courier delivery period | Неправильний період кур'єрської доставки |
| 106 | Shipping date less than availability date | Дата доставки менше дати наявності |
| 107 | Delivery period less than availability time | Термін доставки менше часу наявності |
| 108 | Incorrect payment method type | Неправильний тип платежу |
| 109 | Products from different sellers must be in different orders | Товари від різних продавців — у різних замовленнях |
| 110 | Inadmissible address | Недійсна адреса |
| 111 | Incorrect min insurance amount | Неправильна мінімальна вартість страховки |
| 112 | Shipping by cash on delivery is forbidden | Відправка післяплатою заборонена |
| 113 | Order reservation possible only until the end of the day | Бронювання можливе тільки до кінця доби |
| 114 | Incorrect file type | Неправильний тип файлу |
| 115 | Too many requests | Перевищення частоти запитів (макс. 3/сек) |

---

## 12. Формування URL для зображення товару

URL картинки формується з коду товару за шаблоном:

```
https://opt.brain.com.ua/static/images/prod_img/{передостанній символ коду}/{останній символ коду}/{код товару}.jpg
```

**Приклад:**

Код товару: `U0002094`  
→ передостанній символ: `9`, останній символ: `4`

```
https://opt.brain.com.ua/static/images/prod_img/9/4/U0002094.jpg
```

**Розміри зображень:**

| Суфікс | Розмір |
|---|---|
| `_small` | мале зображення |
| *(без суфікса)* | середнє зображення |
| `_big` | велике зображення |
| `_main` | повнорозмірне зображення |

**Приклад для кількох розмірів (код `S1234567`):**
```
https://opt.brain.com.ua/static/images/prod_img/6/7/S1234567_small.jpg
https://opt.brain.com.ua/static/images/prod_img/6/7/S1234567.jpg
https://opt.brain.com.ua/static/images/prod_img/6/7/S1234567_big.jpg
https://opt.brain.com.ua/static/images/prod_img/6/7/S1234567_main.jpg
```
