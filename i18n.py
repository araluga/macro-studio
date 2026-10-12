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
    "Click to change the hotkey": "Нажмите, чтобы сменить клавишу",

    # tray and emergency stop
    "Show window": "Показать окно",
    "Quit": "Выход",
    "click this icon to stop": "нажмите на значок, чтобы остановить",
    "Corner emergency stop": "Аварийная остановка в углу",
    "Move the mouse into the top-left corner of the screen to stop playback or monitoring. Works even when hotkeys can't (e.g. over admin windows).":
        "Уведите мышь в левый верхний угол экрана, чтобы остановить воспроизведение или мониторинг. Работает, даже когда горячие клавиши не срабатывают (например, поверх окон администратора).",
    "Emergency stop: the mouse was moved into the top-left corner.":
        "Аварийная остановка: мышь уведена в левый верхний угол.",

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
    "Wait until the image disappears": "Ждать, пока картинка исчезнет",
    "After a run, the macro can fire again only once the image has left the screen.":
        "После срабатывания макрос сработает снова, только когда картинка пропадёт с экрана.",
    "Max runs per monitoring session": "Лимит срабатываний за сеанс",
    "0 — unlimited. Protects against endless runs if the macro doesn't remove the image.":
        "0 — без лимита. Защищает от бесконечных запусков, если макрос не убирает картинку.",
    "Play only when the image is found": "Воспроизводить, только если картинка найдена",
    "On Play, a repeat is skipped if the image isn't on screen, instead of clicking at the recorded spots.":
        "При воспроизведении повтор пропускается, если картинки нет на экране, вместо кликов по записанным местам.",
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

    # command card
    "Run a command": "Запуск команды",
    "Run a command when this macro runs": "Запускать команду вместе с этим макросом",
    "A cmd or PowerShell script written in advance. It runs every time this macro runs: on Play, or when its image trigger fires.":
        "Заранее написанная команда cmd или PowerShell. Выполняется каждый раз, когда запускается макрос: при воспроизведении или при срабатывании триггера по картинке.",
    "Shell": "Оболочка",
    "When": "Когда",
    "Before the clicks": "До кликов",
    "After the clicks": "После кликов",
    "Variables: MACRO_NAME, MATCH_X and MATCH_Y (center of the found image), MATCH_W, MATCH_H, MATCH_SCORE — write %MATCH_X% in cmd or $env:MATCH_X in PowerShell. The command runs in your user folder with your account's rights.":
        "Переменные: MACRO_NAME, MATCH_X и MATCH_Y (центр найденной картинки), MATCH_W, MATCH_H, MATCH_SCORE — пишите %MATCH_X% в cmd или $env:MATCH_X в PowerShell. Команда выполняется в папке пользователя с правами вашей учётной записи.",
    "Wait until it finishes": "Ждать завершения",
    "The output and exit code go to the log; the stop key ends the command. Turn off to start it in the background.":
        "Вывод и код возврата попадут в журнал, клавиша остановки прерывает команду. Если выключить, команда запустится в фоне.",
    "Show the console window": "Показывать окно консоли",
    "Otherwise the command runs hidden.": "Иначе команда выполняется скрыто.",
    "Test the command": "Проверить команду",
    "Run the command now, without clicks": "Выполнить команду сейчас, без кликов",
    "For example:": "Например:",
    "Write a command first.": "Сначала напишите команду.",
    "command only": "только команда",
    "Command of “{name}” started (PID {pid}).": "Команда «{name}» запущена (PID {pid}).",
    "Command of “{name}” finished with code {code}.": "Команда «{name}» завершилась с кодом {code}.",
    "Command of “{name}” was stopped.": "Команда «{name}» остановлена.",
    "Command error: {err}": "Ошибка команды: {err}",
    "Some imported macros contain terminal commands: {names}.\n\nThey were switched off. Read each command before turning it on — a command from someone else can do anything your account can.":
        "Некоторые импортированные макросы содержат команды терминала: {names}.\n\nОни выключены. Прочитайте каждую команду, прежде чем включать её: чужая команда может сделать всё, что доступно вашей учётной записи.",

    # playback card
    "Playback": "Воспроизведение",
    "How to replay the recorded actions.": "Как повторять записанные действия.",
    "Repeats": "Повторов",
    "0 — forever, until you press {key}": "0 — бесконечно, пока не нажмёте {key}",
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
    "The damaged file was renamed to:\n{path}\nso it won't be overwritten.":
        "Повреждённый файл переименован в:\n{path}\nчтобы он не перезаписался.",
    "New macros will be saved to:\n{path}\nso the damaged file won't be overwritten.":
        "Новые макросы будут сохраняться в:\n{path}\nчтобы повреждённый файл не перезаписался.",
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
    "Ready. {record} — record, {play} — play, {watch} — monitor, {stop} — stop.":
        "Готово. {record} — запись, {play} — воспроизвести, {watch} — мониторинг, {stop} — стоп.",
    "Stop the current action first ({key}).": "Сначала остановите текущее действие ({key}).",
    "Overwrite the actions of macro “{name}”?": "Перезаписать действия макроса «{name}»?",
    "Preparing to record…": "Подготовка к записи…",
    " Image found ({score}%) — clicks will be anchored to it.":
        " Картинка найдена ({score}%) — клики будут привязаны к ней.",
    " Image not on screen ({score}%) — no anchor.": " Картинки на экране нет ({score}%) — без привязки.",
    "Recording “{name}” started. {key} — stop.": "Запись «{name}» началась. {key} — остановить.",
    "REC  {time}   ·   {events}   ·   {key} — stop": "ЗАПИСЬ  {time}   ·   {events}   ·   {key} — стоп",
    "Recording stopped: {events}.": "Запись остановлена: {events}.",
    "This macro has no recorded actions or command — press “Record” or add a command.":
        "В макросе нет ни записанных действий, ни команды — нажмите «Записать» или добавьте команду.",
    "{n} of {total}": "{n} из {total}",
    "PLAYING  “{name}”   ·   {progress}   ·   {key} — stop":
        "ВОСПРОИЗВЕДЕНИЕ  «{name}»   ·   {progress}   ·   {key} — стоп",
    "WAITING FOR IMAGE  “{name}”   ·   {key} — stop": "ЖДУ КАРТИНКУ  «{name}»   ·   {key} — стоп",
    "Image for “{name}” not found ({score}%) — waiting for it, repeats are skipped.":
        "Картинка для «{name}» не найдена ({score}%) — жду её, повторы пропускаются.",
    "Image for “{name}” not found ({score}%) — clicking at the recorded positions.":
        "Картинка для «{name}» не найдена ({score}%) — клики идут по записанным координатам.",
    "Playback of “{name}” finished ({times}).": "Воспроизведение «{name}» завершено ({times}).",
    "Playback error: {err}": "Ошибка воспроизведения: {err}",
    "No macros with an enabled trigger, an image and recorded actions.":
        "Нет макросов, у которых включён триггер, добавлена картинка и записаны действия.",
    "Monitoring started: {names}": "Мониторинг запущен: {names}",
    "Found “{name}” ({score}%) at ({x}, {y}) — running": "Найдено «{name}» ({score}%) в ({x}, {y}) — выполняю",
    ", offset {offset}": ", сдвиг {offset}",
    "RUNNING  “{name}”   ·   {key} — stop": "ВЫПОЛНЯЕТСЯ  «{name}»   ·   {key} — стоп",
    "MONITORING   ·   {parts}   ·   fired: {n}   ·   {key} — stop":
        "МОНИТОРИНГ   ·   {parts}   ·   сработало: {n}   ·   {key} — стоп",
    "“{name}” reached its limit of {n} runs.": "«{name}» достиг лимита: {n} срабатываний.",
    "All macros reached their run limit — monitoring stopped.":
        "Все макросы достигли лимита срабатываний — мониторинг остановлен.",
    "Monitoring error: {err}": "Ошибка мониторинга: {err}",
    "Monitoring stopped. Triggered: {n}.": "Мониторинг остановлен. Срабатываний: {n}.",
    "“{name}”": "«{name}»",
}
