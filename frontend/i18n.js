// Only presentation labels are translated. Catalog IDs, form values and the API
// payload retain their original values; server explanations are left untouched.
const messages = {
  'Подбор подрядчиков для вашего события с объяснением каждого варианта.': ['Іс-шараңызға мамандарды таңдап, әр ұсыныстың себебін түсіндіреміз.', 'Find event professionals with a clear reason for every recommendation.'],
  'Повод — люди для вашего события': ['Повод — іс-шараңызға лайық мамандар', 'Povod — people for your event'],
  'Перейти к подбору': ['Іріктеуге өту', 'Skip to search'],
  'Подрядчики для ваших событий': ['Іс-шараңызға лайық мамандар', 'People for your events'],
  'Открыть демо': ['Демоны көру', 'Explore demo'],
  'Перейти к сервису': ['Сервиске өту', 'Start your search'],
  'МЕНЬШЕ ПОИСКА. БОЛЬШЕ СОВПАДЕНИЙ.': ['АЗ ІЗДЕҢІЗ. ДӘЛ ТАҢДАҢЫЗ.', 'LESS SEARCHING. MORE CONNECTIONS.'],
  'Найдите своих людей': ['Іс-шараңызға лайық', 'Find your people'],
  'для вашего события': ['мамандарды табыңыз', 'for your event'],
  'До трёх подходящих подрядчиков. С понятным объяснением каждого выбора.': ['Үшке дейін лайық маман. Әр ұсыныстың себебі түсінікті.', 'Up to three matching professionals. A clear reason for every choice.'],
  'до': ['ең көбі', 'up to'],
  'вариантов': ['нұсқа', 'options'],
  'Остановить анимацию': ['Анимацияны тоқтату', 'Pause animation'],
  'Продолжить анимацию': ['Анимацияны жалғастыру', 'Resume animation'],
  'События: свадьбы, корпоративы, конференции, юбилеи и ваш особенный повод': ['Іс-шаралар: үйлену тойлары, корпоративтер, конференциялар, мерейтойлар және ерекше қуанышыңыз', 'Events: weddings, company events, conferences, anniversaries and your special occasion'],
  'Свадьбы': ['Үйлену тойлары', 'Weddings'],
  'Корпоративы': ['Корпоративтер', 'Company events'],
  'Конференции': ['Конференциялар', 'Conferences'],
  'Юбилеи': ['Мерейтойлар', 'Anniversaries'],
  'Ваш особенный повод': ['Ерекше қуанышыңыз', 'Your special occasion'],
  'Вы в демонстрационном режиме': ['Бұл — демо режим', 'You’re exploring the demo'],
  'Здесь показаны готовые примеры. Чтобы подобрать людей под свои условия, перейдите к сервису.': ['Мұнда дайын мысалдар көрсетілген. Өз шарттарыңызға сай мамандарды табу үшін сервиске өтіңіз.', 'These are saved examples. Start your own search to find people who match your needs.'],
  'Посмотреть сценарий': ['Сценарийді көру', 'Choose an example'],
  'Три рекомендации': ['Үш ұсыныс', 'Three recommendations'],
  'Редкая категория — два варианта': ['Сирек санат — екі нұсқа', 'Rare category — two options'],
  'В городе нет категории': ['Қалада бұл санат жоқ', 'Category unavailable in this city'],
  'Никто не проходит по бюджету': ['Бюджетке сай маман жоқ', 'No matches within budget'],
  'Ошибка соединения': ['Байланыс қатесі', 'Connection error'],
  'Расскажите о событии': ['Іс-шараңыз туралы айтыңыз', 'Tell us about your event'],
  'Пять основных параметров — и можно выбирать.': ['Бес негізгі шартты көрсетіп, таңдауға көшіңіз.', 'Just five details, then you can explore your options.'],
  'Изменить параметры': ['Шарттарды өзгерту', 'Edit your search'],
  'Выбранные параметры события': ['Іс-шараның таңдалған шарттары', 'Your event details'],
  'Параметры вашего события': ['Іс-шараңыздың шарттары', 'Your event details'],
  'Параметры демо-сценария': ['Демо сценарий шарттары', 'Demo event details'],
  '0 из 5 заполнено': ['5 өрістің 0-і толтырылды', '0 of 5 completed'],
  '{count} из {total} заполнено': ['{total} өрістің {count}-і толтырылды', '{count} of {total} completed'],
  'Готовим варианты для вашей формы…': ['Таңдау нұсқаларын дайындап жатырмыз…', 'Preparing your search options…'],
  'Загружаем параметры каталога…': ['Каталог параметрлері жүктелуде…', 'Loading catalog options…'],
  'Примеры запросов': ['Іздеу мысалдары', 'Example searches'],
  'Можно начать с примера': ['Мысалдан бастауға болады', 'Try an example to get started'],
  'Низкий бюджет': ['Шағын бюджет', 'Small budget'],
  'Что вы планируете?': ['Не жоспарлап отырсыз?', 'What are you planning?'],
  'Формат события': ['Іс-шара форматы', 'Event type'],
  'Кого ищем?': ['Кімді іздейміз?', 'Who do you need?'],
  'Где и когда встречаемся?': ['Қайда және қашан кездесеміз?', 'Where and when?'],
  'Город': ['Қала', 'City'],
  'Дата': ['Күні', 'Date'],
  'Кого ищем': ['Қажет маман', 'Professional'],
  'Событие': ['Іс-шара', 'Event'],
  'Бюджет': ['Бюджет', 'Budget'],
  'Язык': ['Тіл', 'Language'],
  'Длительность': ['Ұзақтығы', 'Duration'],
  'Комфортный для вас бюджет': ['Өзіңізге қолайлы бюджет', 'A budget you’re comfortable with'],
  'До какой суммы, ₸': ['Ең жоғары сома, ₸', 'Maximum budget, ₸'],
  'Укажите сумму': ['Соманы көрсетіңіз', 'Enter an amount'],
  'Верхний предел бюджета, тенге': ['Бюджеттің жоғарғы шегі, теңге', 'Maximum budget in tenge'],
  'Например, 500 000': ['Мысалы, 500 000', 'For example, 500,000'],
  'Передвиньте ползунок или укажите точную сумму.': ['Жүгірткіні жылжытыңыз немесе нақты соманы енгізіңіз.', 'Move the slider or enter an exact amount.'],
  'Ещё пара пожеланий': ['Қосымша тілектеріңіз', 'A few more preferences'],
  'необязательно': ['міндетті емес', 'optional'],
  'На сколько часов?': ['Қанша сағатқа?', 'For how many hours?'],
  'Например, 4.5': ['Мысалы, 4.5', 'For example, 4.5'],
  'Язык общения': ['Қарым-қатынас тілі', 'Preferred language'],
  'Подобрать подрядчиков': ['Мамандарды табу', 'Find my matches'],
  'Только рекомендации. Никаких заявок и обязательств.': ['Тек ұсыныстар. Өтінім де, міндеттеме де жоқ.', 'Just recommendations. No booking or commitment.'],
  '* Нужны для подбора': ['* Іріктеу үшін қажет', '* Needed to find your matches'],
  'Ваша подборка': ['Сізге арналған ұсыныстар', 'Your matches'],
  'Сравните условия и причины, по которым подходит каждый вариант.': ['Шарттарды және әр маманның сізге неге сай келетінін салыстырыңыз.', 'Compare the details and see why each option fits.'],
  'ДО 3 ВАРИАНТОВ': ['3 НҰСҚАҒА ДЕЙІН', 'UP TO 3 OPTIONS'],
  'Вы изменили пожелания. Обновите подборку, чтобы увидеть подходящие варианты.': ['Шарттарыңыз өзгерді. Сәйкес нұсқаларды көру үшін қайта іздеңіз.', 'Your preferences have changed. Search again to see updated matches.'],
  'Хороший выбор начинается с понятных причин.': ['Жақсы таңдау түсінікті себептерден басталады.', 'Good choices start with clear reasons.'],
  'Условия работы уточняются у подрядчика.': ['Қызмет шарттарын маманмен нақтылаңыз.', 'Confirm service details with the professional.'],
  'Включите JavaScript, чтобы заполнить форму и получить подборку.': ['Нысанды толтырып, ұсыныстар алу үшін JavaScript-ті қосыңыз.', 'Enable JavaScript to fill in the form and get recommendations.'],
  'Выберите город': ['Қаланы таңдаңыз', 'Choose a city'],
  'Какой у вас повод?': ['Қандай іс-шара өткізесіз?', 'What’s the occasion?'],
  'Выберите специалиста': ['Маманды таңдаңыз', 'Choose a professional'],
  'Любой': ['Кез келген', 'Any'],
  'Не указана': ['Көрсетілмеген', 'Not specified'],
  'Не задан': ['Көрсетілмеген', 'Not set'],
  'Менее 1 мин': ['1 минуттан аз', 'Less than 1 min'],
  '{hours} ч': ['{hours} сағ', '{hours} hr'],
  '{minutes} мин': ['{minutes} мин', '{minutes} min'],
  'До {price} ₸': ['{price} ₸ дейін', 'Up to ₸{price}'],
  'до {price} ₸': ['{price} ₸ дейін', 'up to ₸{price}'],
  'От {price} ₸': ['{price} ₸ бастап', 'From ₸{price}'],
  'от {price} ₸': ['{price} ₸ бастап', 'from ₸{price}'],
  'Бюджет не задан': ['Бюджет көрсетілмеген', 'Budget not set'],
  'Заполните это поле.': ['Бұл өрісті толтырыңыз.', 'Please fill in this field.'],
  'Введите целую сумму больше 0 ₸.': ['0 ₸-ден үлкен бүтін соманы енгізіңіз.', 'Enter a whole amount greater than ₸0.'],
  'Введите число часов больше 0.': ['0-ден үлкен сағат санын енгізіңіз.', 'Enter a duration greater than 0 hours.'],
  'Введите корректное число часов.': ['Сағат санын дұрыс енгізіңіз.', 'Enter a valid number of hours.'],
  'Укажите корректную дату.': ['Күнді дұрыс көрсетіңіз.', 'Enter a valid date.'],
  'Выберите дату с {min} по {max}.': ['{min} мен {max} аралығындағы күнді таңдаңыз.', 'Choose a date between {min} and {max}.'],
  'Календарь: {min}–{max}': ['Күнтізбе: {min}–{max}', 'Calendar: {min}–{max}'],
  'Изменить пожелания': ['Шарттарды өзгерту', 'Adjust your preferences'],
  'Подбираем варианты…': ['Нұсқаларды іздеп жатырмыз…', 'Finding your matches…'],
  'Подбираем подрядчиков.': ['Мамандарды іріктеп жатырмыз.', 'Finding matching professionals.'],
  'В городе нет этой категории': ['Бұл қалада осы санат жоқ', 'This category isn’t available in this city'],
  'Нет подходящих вариантов': ['Сәйкес нұсқалар табылмады', 'No matching options'],
  'Попробуем ещё раз?': ['Қайталап көрейік пе?', 'Shall we try again?'],
  'Повторить': ['Қайталау', 'Try again'],
  'Повторить загрузку': ['Қайта жүктеу', 'Reload'],
  'Календарь каталога закончился. Для реального подбора нужны новые данные; демо доступно по ссылке сверху.': ['Каталог күнтізбесінің мерзімі аяқталды. Іріктеу үшін жаңа деректер қажет. Жоғарғы сілтеме арқылы демоны көруге болады.', 'The catalog calendar has ended. Live matching needs updated data; you can still explore the demo using the link above.'],
  'Подбираем вашу команду': ['Сізге лайық команданы іздеп жатырмыз', 'Finding your people'],
  'Ваша следующая хорошая команда': ['Іс-шараңызға лайық команда', 'Your next great team'],
  'Проверяем условия и готовим объяснение для каждого варианта.': ['Шарттарды тексеріп, әр ұсыныстың себебін дайындап жатырмыз.', 'Checking your needs and preparing a reason for each recommendation.'],
  'Укажите параметры выше. Здесь появятся до трёх вариантов — каждый с объяснением, ценой и важными деталями.': ['Жоғарыда шарттарды көрсетіңіз. Мұнда үшке дейін нұсқа пайда болады — әрқайсысының себебі, бағасы және маңызды мәліметтері көрсетіледі.', 'Enter your details above. Up to three options will appear here, each with a reason, price and key details.'],
  'Почему подходит': ['Неге сізге сай келеді', 'Why this is a match'],
  'Что учесть': ['Нені ескеру керек', 'Things to consider'],
  'Связаться ↗': ['Байланысу ↗', 'Get in touch ↗'],
  'Доступно в полной версии. Сейчас сервис помогает подобрать подрядчика.': ['Толық нұсқада қолжетімді. Қазір сервис маманды таңдауға көмектеседі.', 'Available in the full version. For now, the service helps you choose a professional.'],
  'Синтетический профиль': ['Жасанды профиль', 'Synthetic profile'],
  'Цена проставлена при подготовке датасета': ['Баға деректер жиынын дайындау кезінде енгізілген', 'Price supplied during dataset preparation'],
  'Город проставлен при подготовке датасета': ['Қала деректер жиынын дайындау кезінде енгізілген', 'City supplied during dataset preparation'],
  'Черновик сохранён на этом устройстве': ['Нобай осы құрылғыда сақталды', 'Draft saved on this device'],
  'Автосохранение недоступно в этом браузере': ['Бұл браузерде автоматты сақтау қолжетімсіз', 'Autosave is unavailable in this browser'],
  'Черновик восстановлен на этом устройстве': ['Нобай осы құрылғыдан қалпына келтірілді', 'Draft restored on this device'],
  'Не удалось восстановить черновик. Можно заполнить форму заново.': ['Нобайды қалпына келтіру мүмкін болмады. Нысанды қайта толтыруға болады.', 'We couldn’t restore your draft. You can fill in the form again.'],
  'Сервис вернул неполный ответ. Попробуйте повторить запрос.': ['Сервистің жауабы толық емес. Қайта сұрау жіберіп көріңіз.', 'The service returned an incomplete response. Please try again.'],
  'Не удалось получить параметры каталога. Попробуйте ещё раз.': ['Каталог параметрлерін алу мүмкін болмады. Қайталап көріңіз.', 'We couldn’t load the catalog options. Please try again.'],
  'Сервис не принял параметры. Проверьте отмеченные поля и повторите подбор.': ['Сервис параметрлерді қабылдамады. Белгіленген өрістерді тексеріп, қайта іздеңіз.', 'The service couldn’t accept these details. Check the highlighted fields and search again.'],
  'Сервис временно недоступен (HTTP {status}). Попробуйте ещё раз.': ['Сервис уақытша қолжетімсіз (HTTP {status}). Қайталап көріңіз.', 'The service is temporarily unavailable (HTTP {status}). Please try again.'],
  'Сервис вернул ответ в неверном формате. Попробуйте ещё раз.': ['Сервис қате форматта жауап берді. Қайталап көріңіз.', 'The service returned an invalid response. Please try again.'],
  'Сервис не ответил за 15 секунд. Повторите запрос.': ['Сервис 15 секунд ішінде жауап бермеді. Сұрауды қайталаңыз.', 'The service didn’t respond within 15 seconds. Please try again.'],
  'Не удалось связаться с сервисом. Проверьте подключение и убедитесь, что сервис подбора запущен.': ['Сервиспен байланысу мүмкін болмады. Интернет байланысын және іріктеу сервисінің жұмыс істеп тұрғанын тексеріңіз.', 'We couldn’t reach the service. Check your connection and make sure the matching service is running.'],
  'Демонстрация ошибки соединения. Попробуйте повторить запрос.': ['Байланыс қатесінің демо мысалы. Сұрауды қайталап көріңіз.', 'This is a demo connection error. Try the request again.'],
  'Каталог подрядчиков': ['Мамандар каталогы', 'Professional directory'],
  'Все категории': ['Барлық санаттар', 'All categories'],
  'Все города': ['Барлық қалалар', 'All cities'],
  'Найти по имени': ['Аты бойынша іздеу', 'Search by name'],
  'Найти по имени или ID': ['Аты немесе ID бойынша іздеу', 'Search by name or ID'],
  'Имя или ID подрядчика': ['Маманның аты немесе ID', 'Professional’s name or ID'],
  'Город каталога': ['Каталогтағы қала', 'Catalog city'],
  'Категория подрядчика': ['Маман санаты', 'Professional category'],
  'Календарь: {start} — {end}': ['Күнтізбе: {start} — {end}', 'Calendar: {start} — {end}'],
  'Показать ещё': ['Тағы көрсету', 'Show more'],
  'Форматы': ['Форматтар', 'Event types'],
  'Языки': ['Тілдер', 'Languages'],
  'На площадке': ['Іс-шара орнында', 'Time on site'],
  'Не привязано к часам': ['Сағатпен шектелмейді', 'Not tied to hours'],
  'Без привязки к часам присутствия': ['Қатысу сағатымен шектелмейді', 'No on-site time limit'],
  'До {hours} ч': ['{hours} сағатқа дейін', 'Up to {hours} hours'],
  'Занято дней': ['Бос емес күндер', 'Booked days'],
  '{busy} из 100 · в декабре {december} из 31': ['100 күннің {busy}-і · желтоқсанда 31 күннің {december}-і', '{busy} of 100 · December: {december} of 31'],
  'Описание на русском': ['Сипаттама орыс тілінде', 'Description in Russian'],
  'Текст сервиса на русском': ['Сервис мәтіні орыс тілінде', 'Service response in Russian'],
  'Профили из исходного каталога. Доступность на дату проверяется при подборе.': ['Бастапқы каталогтағы профильдер. Таңдалған күнге қолжетімділік іріктеу кезінде тексеріледі.', 'Profiles from the original catalog. Availability for your date is checked when you search.'],
  'Показано {shown} из {total}': ['{total} профильдің {shown}-і көрсетілді', 'Showing {shown} of {total}'],
  'Занятых дней: {count}': ['Бос емес күндер: {count}', 'Booked days: {count}'],
  'Переключить на тёмную тему': ['Қараңғы тақырыпқа ауысу', 'Switch to dark mode'],
  'Переключить на светлую тему': ['Жарық тақырыпқа ауысу', 'Switch to light mode'],
  'Тёмная тема': ['Қараңғы тақырып', 'Dark mode'],
  'Светлая тема': ['Жарық тақырып', 'Light mode'],
  'Тема оформления': ['Көрініс тақырыбы', 'Appearance'],
  'Язык интерфейса': ['Интерфейс тілі', 'Interface language'],
  'Помочь с подбором': ['Маман таңдауға көмектесейін', 'Help me choose'],
  'Подбор подрядчиков': ['Мамандарды іріктеу', 'Find event professionals'],
  'Опишите событие — я уточню детали': ['Іс-шараны сипаттаңыз — мәліметтерін нақтылаймын', 'Describe your event — I’ll ask about the details'],
  'Отправить': ['Жіберу', 'Send'],
  'Закрыть чат': ['Чатты жабу', 'Close chat'],
  'Сообщение помощнику': ['Көмекшіге хабарлама', 'Message the assistant'],
  'Чат пока работает на русском': ['Чат әзірге орыс тілінде жұмыс істейді', 'The chat currently works in Russian'],
  'Посмотреть каталог': ['Каталогты көру', 'Explore the directory'],
  'Каталог': ['Каталог', 'Directory'],
  'Ничего не найдено': ['Ештеңе табылмады', 'No results found'],
  'Попробуйте другую категорию, город или имя.': ['Басқа санатты, қаланы немесе атты іздеп көріңіз.', 'Try another category, city or name.'],
  'Сбросить фильтры': ['Сүзгілерді тазарту', 'Clear filters'],
  'Подробнее': ['Толығырақ', 'View details'],
  'О профиле': ['Профиль туралы', 'About this profile'],
  'Цена дополнена в датасете': ['Баға деректер жиынына кейін енгізілген', 'Price supplied in the dataset'],
  'Город дополнен в датасете': ['Қала деректер жиынына кейін енгізілген', 'City supplied in the dataset'],
  'Скрыть': ['Жасыру', 'Show less'],
  'Нет описания': ['Сипаттама жоқ', 'No description available'],
  'Алматы': ['Алматы', 'Almaty'],
  'Астана': ['Астана', 'Astana'],
  'Зарубежье': ['Шетел', 'Abroad'],
  'Банкетный зал': ['Банкет залы', 'Banquet hall'],
  'Ведущий': ['Жүргізуші', 'Event host'],
  'Ведущий церемонии': ['Рәсім жүргізушісі', 'Ceremony host'],
  'Видеограф': ['Видеограф', 'Videographer'],
  'Декоратор': ['Безендіруші', 'Decorator'],
  'Загородная площадка': ['Қала сыртындағы алаң', 'Countryside venue'],
  'Инструменталист': ['Аспапта орындаушы', 'Instrumentalist'],
  'Лайв-бэнд': ['Жанды музыка тобы', 'Live band'],
  'Национальный ансамбль': ['Ұлттық ансамбль', 'Traditional ensemble'],
  'Отель': ['Қонақүй', 'Hotel'],
  'Подарки и сувениры': ['Сыйлықтар мен кәдесыйлар', 'Gifts and souvenirs'],
  'Ресторан': ['Мейрамхана', 'Restaurant'],
  'Танцевальный коллектив': ['Би ұжымы', 'Dance group'],
  'Флорист': ['Флорист', 'Florist'],
  'Фото и видеобудки': ['Фото және видеобудкалар', 'Photo and video booths'],
  'Фотограф': ['Фотограф', 'Photographer'],
  'Шоу-программа': ['Шоу-бағдарлама', 'Show entertainment'],
  'день рождения': ['туған күн', 'birthday'],
  'конференция': ['конференция', 'conference'],
  'корпоратив': ['корпоратив', 'company event'],
  'свадьба': ['үйлену тойы', 'wedding'],
  'той': ['той', 'toi celebration'],
  'юбилей': ['мерейтой', 'anniversary'],
  'День рождения': ['Туған күн', 'Birthday'],
  'Конференция': ['Конференция', 'Conference'],
  'Корпоратив': ['Корпоратив', 'Company event'],
  'Свадьба': ['Үйлену тойы', 'Wedding'],
  'Той': ['Той', 'Toi celebration'],
  'Юбилей': ['Мерейтой', 'Anniversary'],
  'английский': ['ағылшын', 'English'],
  'казахский': ['қазақ', 'Kazakh'],
  'русский': ['орыс', 'Russian'],
};
const supported = ['ru', 'kk', 'en'];
const intlLocales = { ru: 'ru-RU', kk: 'kk-KZ', en: 'en-GB' };
const storageKey = 'povod:locale';
let current = 'ru';
const textSources = new WeakMap();
const attributeSources = new WeakMap();
const boundSelectors = new WeakSet();

export function language() { return current; }
export function locale() { return intlLocales[current]; }

export function t(source, vars = {}) {
  if (source == null) return '';
  const key = String(source);
  const translated = current === 'ru' ? key : messages[key]?.[current === 'kk' ? 0 : 1] ?? key;
  return translated.replace(/\{([\w]+)\}/g, (placeholder, name) => Object.hasOwn(vars, name) ? String(vars[name]) : placeholder);
}

// Text nodes retain their original Russian copy so repeated language changes do
// not translate translations. No markup, input value or option value is changed.
export function translateTree(root = document) {
  const owner = root.ownerDocument || root;
  const walker = owner.createTreeWalker(root, 4);
  let node;
  while ((node = walker.nextNode())) {
    if (node.parentElement?.closest('script, style, noscript, #contractor-assistant-root, [data-original], [data-i18n-ignore]')) continue;
    const actual = node.nodeValue;
    let entry = textSources.get(node);
    if (!entry || actual !== entry.rendered) entry = { source: actual, rendered: actual };
    const match = entry.source.match(/^(\s*)([\s\S]*?)(\s*)$/);
    const key = match[2];
    if (key) {
      const rendered = `${match[1]}${t(key)}${match[3]}`;
      if (actual !== rendered) node.nodeValue = rendered;
      entry.rendered = rendered;
      textSources.set(node, entry);
    }
  }
  const elements = [...(root.nodeType === 1 ? [root] : []), ...root.querySelectorAll('[aria-label], [placeholder], [title], meta[name="description"]')];
  for (const element of elements) {
    if (element.closest('script, style, #contractor-assistant-root, [data-original], [data-i18n-ignore]')) continue;
    const stored = attributeSources.get(element) || {};
    const attributes = ['aria-label', 'placeholder', 'title'];
    if (element.matches('meta[name="description"]')) attributes.push('content');
    for (const attribute of attributes) {
      const actual = element.getAttribute(attribute);
      if (actual == null) continue;
      let entry = stored[attribute];
      if (!entry || actual !== entry.rendered) entry = { source: actual, rendered: actual };
      entry.rendered = t(entry.source);
      if (actual !== entry.rendered) element.setAttribute(attribute, entry.rendered);
      stored[attribute] = entry;
    }
    attributeSources.set(element, stored);
  }
}

export function setLanguage(value) {
  current = supported.includes(value) ? value : 'ru';
  try { localStorage.setItem(storageKey, current); } catch { /* UI remains usable without storage. */ }
  document.documentElement.lang = current;
  const selector = document.querySelector('#locale-select');
  if (selector) selector.value = current;
  translateTree();
  document.dispatchEvent(new CustomEvent('localechange', { detail: { language: current, locale: locale() } }));
}

export function initializeLocale() {
  let saved = 'ru';
  try { saved = localStorage.getItem(storageKey) || 'ru'; } catch { /* Default to Russian. */ }
  const selector = document.querySelector('#locale-select');
  if (selector && !boundSelectors.has(selector)) {
    selector.addEventListener('change', event => setLanguage(event.target.value));
    boundSelectors.add(selector);
  }
  setLanguage(saved);
}
