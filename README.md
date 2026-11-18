# Мой универ

Личное приложение для учёбы: расписание, задания, сессия, оценки, конспекты.
Работает прямо в браузере, данные хранятся у владельца (в браузере и в его Google Диске).

## Приложения для Windows и Android
Код оболочек лежит в `native/`, сборка идёт на GitHub (`.github/workflows/build-apps.yml`).
Готовые файлы: вкладка **Releases** → «Приложения «Мой универ»».

### Секреты репозитория (Settings → Secrets and variables → Actions)
- `GOOGLE_DESKTOP_SECRET` — Client secret ключа «Desktop app» (вход Google в Windows-версии).
- `ANDROID_KEYSTORE_B64` — файл ключа подписи Android в base64.
- `ANDROID_KEYSTORE_PASSWORD` — пароль от этого ключа.

Версии библиотек фиксируются в `package-lock.json` (workflow «Обновить версии и lock-файлы»), за свежестью следит Dependabot.
