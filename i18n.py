"""Interface translations. English is the source language; keys are the English strings."""

LANGS = {"en": "English", "ru": "Русский"}

_lang = "en"


def set_language(lang):
    global _lang
    _lang = lang if lang in LANGS else "en"


def language():
    return _lang


def tr(text, **kwargs):
    s = RU.get(text, text) if _lang == "ru" else text
    return s.format(**kwargs) if kwargs else s


_PLURALS = {
    "event": (("event", "events"), ("событие", "события", "событий")),
    "click": (("click", "clicks"), ("клик", "клика", "кликов")),
    "time": (("time", "times"), ("раз", "раза", "раз")),
}


def count(n, word):
    """'1 click' / '5 clicks', '1 клик' / '3 клика' / '5 кликов'."""
    en, ru = _PLURALS[word]
    if _lang == "ru":
        n10, n100 = n % 10, n % 100
        if n10 == 1 and n100 != 11:
            form = ru[0]
        elif 2 <= n10 <= 4 and not 12 <= n100 <= 14:
            form = ru[1]
        else:
            form = ru[2]
    else:
        form = en[0] if n == 1 else en[1]
    return f"{n} {form}"


RU = {
    # sidebar
    "record · replay · image triggers": "запись · повтор · картинки",
    "MACROS": "МАКРОСЫ",
    "Import / export": "Импорт / экспорт",
    "Import macros…": "Импорт макросов…",
    "Export all macros…": "Экспорт всех макросов…",
    "New macro": "Новый макрос",
    "Record": "Записать",
    "Play": "Воспроизвести",
    "Monitor": "Мониторинг",
    "Stop": "Стоп",
    "Language": "Язык",

    # header
    "Macro name": "Название макроса",
    "Click to rename": "Нажмите, чтобы переименовать",
    "Stop recording": "Остановить запись",
    "Ready": "Готово",
    "Recording": "Идёт запись",
    "Playing": "Воспроизведение",
    "Monitoring": "Мониторинг",
    "{dur} s": "{dur} с",
    "anchored to image ({x}, {y})": "привязка к картинке ({x}, {y})",
    "not anchored to image": "без привязки к картинке",
    "Where the image was when recording started — clicks are shifted relative to this point.":
        "Где была картинка в момент записи — клики сдвигаются относительно этого места.",
    "The image wasn't on screen during recording — clicks use the original coordinates.":
        "Во время записи картинки на экране не было — клики идут по исходным координатам.",

    # trigger card
    "Image trigger": "Триггер по картинке",
    "When this image appears on screen, the macro runs automatically (in monitoring mode).":
        "Когда эта картинка появится на экране, макрос выполнится сам (в режиме мониторинга).",
    "Enable the trigger for this macro": "Включить триггер для этого макроса",
    "Paste": "Вставить",
    "Ctrl+V — from clipboard": "Ctrl+V — из буфера обмена",
    "From screen": "С экрана",
    "Select the image directly on screen": "Выделить картинку прямо на экране",
    "File…": "Файл…",
    "Remove": "Убрать",
    "Search area": "Где искать",
    "Full screen": "Весь экран",
    "Region": "Область",
    "Change…": "Изменить…",
    "Select the area on screen again": "Выделить область на экране заново",
    "Similarity threshold": "Порог схожести",
    "On screen now": "Сейчас на экране",
    "Check": "Проверить",
    "Find the image on screen now and show the similarity": "Найти картинку на экране и показать схожесть",
    "Clicks follow the image": "Клики следуют за картинкой",
    "If the image is somewhere else on screen, the clicks move with it.":
        "Если картинка окажется в другом месте экрана — клики сдвинутся вместе с ней.",
    "Search at different scales": "Искать в разных масштабах",
    "Finds enlarged or shrunk images, but is slower.":
        "Находит увеличенную или уменьшенную картинку, но работает медленнее.",
    "Cooldown after trigger": "Пауза после срабатывания",
    "So the macro doesn't fire again and again on the same image.":
        "Чтобы макрос не запускался много раз подряд на одну и ту же картинку.",
    " s": " с",
    " ms": " мс",
    "found": "найдено",
    "below threshold": "ниже порога",
    "Drop an image here\nor press Ctrl+V": "Перетащите картинку сюда\nили нажмите Ctrl+V",
    "Press “Check”": "Нажмите «Проверить»",
    "Add an image first": "Сначала добавьте картинку",
    "Image added — press “Check”": "Картинка добавлена — нажмите «Проверить»",

    # playback card
    "Playback": "Воспроизведение",
    "How to replay the recorded actions.": "Как повторять записанные действия.",
    "Repeats": "Повторов",
    "0 — forever, until you press F12": "0 — бесконечно, пока не нажмёте F12",
    "Delay between repeats": "Пауза между повторами",
    "Speed": "Скорость",
    "Clicks only": "Только клики",
    "Don't replay mouse movement — jump straight to click points.":
        "Не повторять путь мыши — сразу к местам кликов.",
    "Record keyboard": "Записывать клавиатуру",
    "Key presses are recorded too.": "Нажатия клавиш тоже попадут в запись.",

    # monitoring card
    "Watches the screen and runs macros with an enabled trigger as soon as their image is found.":
        "Следит за экраном и запускает макросы с включённым триггером, как только найдена их картинка.",
    "Start monitoring": "Запустить мониторинг",
    "Stop monitoring": "Остановить мониторинг",
    "Check every": "Проверять каждые",
    "Lower = faster reaction, but more CPU load.": "Меньше — быстрее реакция, но выше нагрузка.",
    "Minimize window": "Сворачивать окно",
    "During playback and monitoring.": "При воспроизведении и мониторинге.",
    "Watching ({n}): {names}": "Будут отслеживаться ({n}): {names}",
    "Nothing to watch yet: enable a trigger, add an image and record actions.":
        "Пока нечего отслеживать: включите триггер, добавьте картинку и запишите действия.",

    # log card
    "Log": "Журнал",
    "Clear": "Очистить",

    # list and dialogs
    "empty — press “Record”": "пусто — нажмите «Записать»",
    "My first macro": "Мой первый макрос",
    "Macro {n}": "Макрос {n}",
    "{name} (copy)": "{name} (копия)",
    "Rename": "Переименовать",
    "Duplicate": "Дублировать",
    "Export…": "Экспортировать…",
    "Delete": "Удалить",
    "Delete macro “{name}”?": "Удалить макрос «{name}»?",
    "Error": "Ошибка",
    "Could not read {path}:\n{err}": "Не удалось прочитать {path}:\n{err}",
    "Save error: {err}": "Ошибка сохранения: {err}",
    "Export": "Экспорт",
    "Import": "Импорт",
    "Macros (*.json)": "Макросы (*.json)",
    "Exported: {path}": "Экспортировано: {path}",
    "Imported macros: {n}": "Импортировано макросов: {n}",
    "Image": "Картинка",
    "The image is too small.": "Картинка слишком маленькая.",
    "Image for “{name}” added ({w}×{h}).": "Картинка для «{name}» добавлена ({w}×{h}).",
    "Clipboard": "Буфер обмена",
    "There is no image in the clipboard.\n\nCopy a sticker (right-click → Copy) or take a screenshot with Win+Shift+S.":
        "В буфере обмена нет картинки.\n\nСкопируйте стикер (ПКМ → Копировать) или сделайте скриншот Win+Shift+S.",
    "Images (*.png *.jpg *.jpeg *.bmp *.webp *.gif);;All files (*.*)":
        "Картинки (*.png *.jpg *.jpeg *.bmp *.webp *.gif);;Все файлы (*.*)",
    "Select the image to search for": "Выделите картинку, которую нужно искать",
    "Select the area to search in": "Выделите область, где искать картинку",
    "Esc / right-click — cancel": "Esc / ПКМ — отмена",
    "Search area: {w}×{h} at ({x}, {y})": "Область поиска: {w}×{h} в ({x}, {y})",
    "search area": "область поиска",
    "Search error: {err}": "Ошибка поиска: {err}",
    "Check “{name}”: similarity {score}% (threshold {thr}%) — {result}, {ms} ms":
        "Проверка «{name}»: схожесть {score}% (порог {thr}%) — {result}, {ms} мс",
    "not found": "не найдено",

    # recording / playback / monitoring
    "Ready. F9 — record, F10 — play, F11 — monitor, F12 — stop.":
        "Готово. F9 — запись, F10 — воспроизвести, F11 — мониторинг, F12 — стоп.",
    "Stop the current action first (F12).": "Сначала остановите текущее действие (F12).",
    "Overwrite the actions of macro “{name}”?": "Перезаписать действия макроса «{name}»?",
    "Preparing to record…": "Подготовка к записи…",
    " Image found ({score}%) — clicks will be anchored to it.":
        " Картинка найдена ({score}%) — клики будут привязаны к ней.",
    " Image not on screen ({score}%) — no anchor.": " Картинки на экране нет ({score}%) — без привязки.",
    "Recording “{name}” started. F9 — stop.": "Запись «{name}» началась. F9 — остановить.",
    "REC  {time}   ·   {events}   ·   F9 — stop": "ЗАПИСЬ  {time}   ·   {events}   ·   F9 — стоп",
    "Recording stopped: {events}.": "Запись остановлена: {events}.",
    "No recorded actions in this macro — press “Record” first.":
        "В макросе нет записанных действий — сначала нажмите «Записать».",
    "{n} of {total}": "{n} из {total}",
    "PLAYING  “{name}”   ·   {progress}   ·   F12 — stop":
        "ВОСПРОИЗВЕДЕНИЕ  «{name}»   ·   {progress}   ·   F12 — стоп",
    "Playback of “{name}” finished ({times}).": "Воспроизведение «{name}» завершено ({times}).",
    "Playback error: {err}": "Ошибка воспроизведения: {err}",
    "No macros with an enabled trigger, an image and recorded actions.":
        "Нет макросов, у которых включён триггер, добавлена картинка и записаны действия.",
    "Monitoring started: {names}": "Мониторинг запущен: {names}",
    "Found “{name}” ({score}%) at ({x}, {y}) — running": "Найдено «{name}» ({score}%) в ({x}, {y}) — выполняю",
    ", offset {offset}": ", сдвиг {offset}",
    "RUNNING  “{name}”   ·   F12 — stop": "ВЫПОЛНЯЕТСЯ  «{name}»   ·   F12 — стоп",
    "MONITORING   ·   {parts}   ·   fired: {n}   ·   F11 — stop":
        "МОНИТОРИНГ   ·   {parts}   ·   сработало: {n}   ·   F11 — стоп",
    "Monitoring error: {err}": "Ошибка мониторинга: {err}",
    "Monitoring stopped. Triggered: {n}.": "Мониторинг остановлен. Срабатываний: {n}.",
    "“{name}”": "«{name}»",
}
