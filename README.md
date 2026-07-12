# Warehouse Helper made on Python + HTML(runs both website and bot)

# Как это работает?
1. При запуске файла main.py происходит две вещи:
    I. Запускается файл bot_code.py
    II. Запускается веб-интерфейс(Flask, локально работающее на 127.0.0.1:5000)
2. Сайт и бот имеют единую aiosqlite базу данных для хранения заказов.
3. Управление заказами синхронизируется между телеграм ботом и веб-интерфейсом


# Для запуска из source кода(RU):
1. Скачайте архив кода
2. Создайте venv:
```bash
python -m venv venv

```

3. Активируйте venv:

* Для Windows (PowerShell):

```powershell
venv/bin/Activate.ps1

```

* Для Linux/macOS (Bash):

```bash
source venv/bin/activate

```

4. Установите зависимости:

```bash
pip install -r requirements.txt

```

5. Запустите код:

```bash
python main.py
```

# How it works
1. After you run main.py two things happen:
    I: bot_code.py gets launched
    II: The web interface gets launched(Flask, runs locally at 127.0.0.1:5000)
2. The website and bot share a single aiosqlite database for storing orders
3. Order management is synced between web and bot.

# To start from sources(ENG):

1. Download zip with code
2. Create venv:

```bash
python -m venv venv

```

3. Activate the venv:

* For Windows (PowerShell):

```powershell
venv/bin/activate.ps1

```

* For Linux/macOS (Bash):

```bash
source venv/bin/activate

```

4. Install requirements:

```bash
pip install -r requirements.txt

```

5. Run the code:

```bash
python main.py

```

