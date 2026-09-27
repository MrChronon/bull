"""Actionable UI copy; keep stable machine codes in the private checkpoint."""
MESSAGES = {
    'NVIDIA_SMI_NOT_FOUND': 'На выбранном компьютере не найден nvidia-smi. Проверьте установку NVIDIA-драйвера и PATH SSH-пользователя.',
    'NVIDIA_SMI_QUERY_FAILED': 'Драйвер не вернул список/датчики GPU. Проверьте nvidia-smi на сервере.',
    'NVIDIA_SMI_TIMEOUT': 'Драйвер слишком долго отвечает на запрос датчиков. Эксперимент остановлен.',
    'GPU_BUSY_CLOSE_OTHER_MODELS_OR_APPS': 'Выбранные GPU заняты. Выгрузите модели в обычной Ollama и остановите другие GPU-задачи, затем продолжите здесь. Чужие процессы не завершались.',
    'OLLAMA_EXE_NOT_FOUND': 'Не найдена Ollama на сервере. В GPU Lab → Пути на сервере укажите полный путь к ollama.exe.',
    'MODELS_DIRECTORY_NOT_FOUND': 'Каталог моделей не найден. Проверьте путь на сервере и права SSH-пользователя в GPU Lab → Пути на сервере.',
    'OLLAMA_START_FAILED': 'Отдельная Ollama завершилась при запуске. Проверьте указанную сборку Ollama и NVIDIA-драйвер на сервере.',
    'LAB_LISTENER_NOT_OWNED': 'Не удалось подтвердить приватный порт запущенной Ollama. Запросы модели не отправлены.',
    'ANOTHER_GPU_LAB_IS_RUNNING': 'На сервере уже работает другая GPU Lab. Завершите её; после разрыва связи дождитесь освобождения lease (до 60 секунд без команд).',
    'GPU_TEMPERATURE_AT_LEAST_85C': 'Датчик показал 85°C или выше. Остановлен только лабораторный процесс. Проверьте охлаждение и дайте GPU остыть.',
    'WORKER_CONNECTION_CLOSED': 'Управляющий процесс недоступен. Проверьте SSH, Windows PowerShell и разрешение запуска служебного скрипта.',
    'WORKER_CONNECTION_LOST': 'Связь с супервизором потеряна. Проверьте SSH, затем продолжите сохранённый эксперимент.',
    'WORKER_TELEMETRY_OR_CONNECTION_LOST': 'Потерян канал управления или датчиков. Проверьте SSH и nvidia-smi, затем продолжите эксперимент.',
    'LAB_SSH_FORWARD_FAILED': 'Не удалось открыть отдельный SSH-туннель. Проверьте выбранное подключение и разрешение TCP forwarding на сервере.',
    'REMOTE_MODEL_FORBIDDEN': 'Это удалённая/cloud-модель. GPU Lab работает только с установленными на сервере локальными моделями.',
    'MODEL_DIGEST_CHANGED': 'Модель изменилась после начала эксперимента. Создайте новый эксперимент, чтобы не смешивать версии.',
    'OLLAMA_VERSION_CHANGED': 'Версия Ollama изменилась. Создайте новый эксперимент.',
    'UNSELECTED_GPU_OBSERVED': 'Процесс обнаружен на невыбранной карте. Эксперимент остановлен: изоляция не подтверждена.',
}


def explain(code): return MESSAGES.get(str(code), str(code))
