**Запуск Проекта**

В PowerShell:

```powershell
cd C:\Users\user\projects\Tabloid
```
Создать виртуальное окружение:

```powershell
Rename-Item .venv .venv_old
py -3.10 -m venv .venv
```

Активировать окружение:

```powershell
.\.venv\Scripts\Activate.ps1
```

Если в PowerShell запрещен запуск скриптов:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Установить зависимости:

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Запустить приложение:

```powershell
python main.py
```

Если `py -3.10` не найден, установить Python 3.10 или создать окружение доступной версией Python:

```powershell
python -m venv .venv
```

Главный файл запуска: [main.py].
