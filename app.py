
import sqlite3
from flask import Flask, jsonify, request, redirect, render_template_string

app = Flask(__name__)
DATABASE = "tasks.db"


def get_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def get_demo_user_id(connection):
    user = connection.execute(
        "SELECT id FROM users WHERE username = ?", ("demo",)
    ).fetchone()

    if user is None:
        connection.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            ("demo", "temporary-placeholder")
        )
        connection.commit()
        user = connection.execute(
            "SELECT id FROM users WHERE username = ?", ("demo",)
        ).fetchone()

    return user["id"]


@app.route("/")
def home():
    connection = get_connection()
    user_id = get_demo_user_id(connection)

    status_filter = request.args.get("status", "all")
    category_filter = request.args.get("category", "all")

    query = "SELECT * FROM tasks WHERE user_id = ?"
    params = [user_id]

    if status_filter == "active":
        query += " AND is_completed = 0"
    elif status_filter == "done":
        query += " AND is_completed = 1"

    if category_filter != "all":
        query += " AND category = ?"
        params.append(category_filter)

    query += " ORDER BY is_completed ASC, id DESC"
    tasks = connection.execute(query, params).fetchall()

    categories = connection.execute(
        "SELECT DISTINCT category FROM tasks WHERE user_id = ? ORDER BY category",
        (user_id,)
    ).fetchall()

    stats = connection.execute("""
        SELECT COUNT(*) AS total,
               SUM(CASE WHEN is_completed = 1 THEN 1 ELSE 0 END) AS done
        FROM tasks
        WHERE user_id = ?
    """, (user_id,)).fetchone()

    connection.close()

    total = stats["total"] or 0
    done = stats["done"] or 0
    active = total - done

    return render_template_string("""
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Task Planner</title>
        <style>
            * { box-sizing: border-box; }

            body {
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: 35px auto;
                padding: 0 16px;
                background: #f3f6f4;
                color: #24352b;
            }

            h1 { color: #286749; }

            form, .task, .stats {
                background: white;
                padding: 18px;
                margin-bottom: 15px;
                border-radius: 12px;
                box-shadow: 0 2px 8px #00000008;
            }

            input, textarea, select, button {
                width: 100%;
                padding: 11px;
                margin-top: 8px;
                margin-bottom: 8px;
                font-size: 15px;
                border: 1px solid #d5ded8;
                border-radius: 6px;
            }

            button {
                background: #286749;
                color: white;
                border: 0;
                cursor: pointer;
            }

            button:hover { background: #1d5037; }

            .delete { background: #b94040; }
            .delete:hover { background: #922d2d; }

            .done { color: #27804a; }
            .completed { opacity: 0.7; }

            .stats {
                display: flex;
                justify-content: space-around;
                gap: 10px;
                text-align: center;
                flex-wrap: wrap;
            }

            .number {
                font-size: 24px;
                font-weight: bold;
            }

            .filters {
                display: flex;
                gap: 10px;
                flex-wrap: wrap;
            }

            .filters > * {
                flex: 1;
                min-width: 140px;
            }

            a { color: #286749; }

            .task h3 { overflow-wrap: anywhere; }

            .task-actions {
                display: flex;
                gap: 8px;
                flex-wrap: wrap;
            }

            .task-actions form {
                flex: 1;
                min-width: 130px;
                padding: 0;
                margin: 0;
                box-shadow: none;
            }

            .edit-link {
                display: inline-block;
                margin: 8px 0 14px;
            }
        </style>
    </head>
    <body>
        <h1>Task Planner</h1>
        <p>Планируй дела и следи за прогрессом.</p>

        <div class="stats">
            <div>
                <div class="number">{{ total }}</div>
                Всего задач
            </div>
            <div>
                <div class="number">{{ active }}</div>
                Активных
            </div>
            <div>
                <div class="number">{{ done }}</div>
                Выполнено
            </div>
        </div>

        <form method="post" action="/tasks">
            <h2>Новая задача</h2>

            <label>Название</label>
            <input name="title" required maxlength="200"
                   placeholder="Например, сделать домашнее задание">

            <label>Описание</label>
            <textarea name="description"
                      placeholder="Что нужно сделать?"></textarea>

            <label>Категория</label>
            <input name="category" maxlength="100"
                   placeholder="Учёба, работа, личное">

            <label>Срок выполнения</label>
            <input type="date" name="deadline">

            <button type="submit">Добавить задачу</button>
        </form>

        <h2>Мои задачи</h2>

        <form method="get" class="filters">
            <select name="status">
                <option value="all"
                    {% if status_filter == 'all' %}selected{% endif %}>
                    Все задачи
                </option>
                <option value="active"
                    {% if status_filter == 'active' %}selected{% endif %}>
                    Активные
                </option>
                <option value="done"
                    {% if status_filter == 'done' %}selected{% endif %}>
                    Выполненные
                </option>
            </select>

            <select name="category">
                <option value="all">Все категории</option>
                {% for item in categories %}
                <option value="{{ item['category'] }}"
                    {% if category_filter == item['category'] %}selected{% endif %}>
                    {{ item['category'] }}
                </option>
                {% endfor %}
            </select>

            <button type="submit">Применить фильтры</button>
        </form>

        {% if tasks %}
            {% for task in tasks %}
            <div class="task {% if task['is_completed'] %}completed{% endif %}">
                <h3>{{ task['title'] }}</h3>

                <p>{{ task['description'] or 'Описание не указано' }}</p>
                <p>Категория: {{ task['category'] or 'Общее' }}</p>
                <p>Срок: {{ task['deadline'] or 'Не указан' }}</p>

                <a class="edit-link"
                   href="/tasks/{{ task['id'] }}/edit">
                    Редактировать задачу
                </a>

                {% if task['is_completed'] %}
                    <p class="done">✓ Задача выполнена</p>
                    <form method="post"
                          action="/tasks/{{ task['id'] }}/reopen">
                        <button type="submit">Вернуть в активные</button>
                    </form>
                {% else %}
                    <form method="post"
                          action="/tasks/{{ task['id'] }}/complete">
                        <button type="submit">Отметить выполненной</button>
                    </form>
                {% endif %}

                <form method="post"
                      action="/tasks/{{ task['id'] }}/delete"
                      onsubmit="return confirm('Удалить эту задачу?')">
                    <button class="delete" type="submit">
                        Удалить задачу
                    </button>
                </form>
            </div>
            {% endfor %}
        {% else %}
            <p>Задач нет. Добавь новую или измени фильтры.</p>
        {% endif %}

        <p>
            <a href="/api/status">Статус API</a> ·
            <a href="/api/tasks">Посмотреть задачи в JSON</a>
        </p>
    </body>
    </html>
    """, tasks=tasks, categories=categories, total=total, active=active,
       done=done, status_filter=status_filter,
       category_filter=category_filter)


@app.route("/tasks", methods=["POST"])
def add_task():
    title = request.form.get("title", "").strip()

    if not title:
        return "Название задачи обязательно", 400

    description = request.form.get("description", "").strip()
    category = request.form.get("category", "").strip() or "Общее"
    deadline = request.form.get("deadline", "").strip() or None

    connection = get_connection()
    user_id = get_demo_user_id(connection)

    connection.execute("""
        INSERT INTO tasks (user_id, title, description, category, deadline)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, title, description, category, deadline))

    connection.commit()
    connection.close()

    return redirect("/")


@app.route("/tasks/<int:task_id>/edit", methods=["GET", "POST"])
def edit_task(task_id):
    connection = get_connection()
    user_id = get_demo_user_id(connection)

    task = connection.execute(
        "SELECT * FROM tasks WHERE id = ? AND user_id = ?",
        (task_id, user_id)
    ).fetchone()

    if task is None:
        connection.close()
        return "Задача не найдена", 404

    if request.method == "POST":
        title = request.form.get("title", "").strip()

        if not title:
            connection.close()
            return "Название задачи обязательно", 400

        description = request.form.get("description", "").strip()
        category = request.form.get("category", "").strip() or "Общее"
        deadline = request.form.get("deadline", "").strip() or None

        connection.execute("""
            UPDATE tasks
            SET title = ?, description = ?, category = ?, deadline = ?
            WHERE id = ? AND user_id = ?
        """, (title, description, category, deadline, task_id, user_id))

        connection.commit()
        connection.close()

        return redirect("/")

    connection.close()

    return render_template_string("""
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Редактирование задачи</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 600px;
                margin: 40px auto;
                padding: 0 16px;
                background: #f3f6f4;
                color: #24352b;
            }

            form {
                background: white;
                padding: 20px;
                border-radius: 12px;
            }

            input, textarea, button {
                box-sizing: border-box;
                width: 100%;
                padding: 11px;
                margin: 8px 0 16px;
                font-size: 15px;
                border: 1px solid #d5ded8;
                border-radius: 6px;
            }

            button {
                background: #286749;
                color: white;
                border: 0;
                cursor: pointer;
            }

            a { color: #286749; }
        </style>
    </head>
    <body>
        <h1>Редактирование задачи</h1>

        <form method="post">
            <label>Название</label>
            <input name="title" required maxlength="200"
                   value="{{ task['title'] }}">

            <label>Описание</label>
            <textarea name="description">{{ task['description'] or '' }}</textarea>

            <label>Категория</label>
            <input name="category" maxlength="100"
                   value="{{ task['category'] or 'Общее' }}">

            <label>Срок выполнения</label>
            <input type="date" name="deadline"
                   value="{{ task['deadline'] or '' }}">

            <button type="submit">Сохранить изменения</button>
        </form>

        <p><a href="/">Вернуться к задачам</a></p>
    </body>
    </html>
    """, task=task)


@app.route("/tasks/<int:task_id>/complete", methods=["POST"])
def complete_task(task_id):
    connection = get_connection()
    user_id = get_demo_user_id(connection)

    connection.execute(
        "UPDATE tasks SET is_completed = 1 WHERE id = ? AND user_id = ?",
        (task_id, user_id)
    )

    connection.commit()
    connection.close()

    return redirect("/")


@app.route("/tasks/<int:task_id>/reopen", methods=["POST"])
def reopen_task(task_id):
    connection = get_connection()
    user_id = get_demo_user_id(connection)

    connection.execute(
        "UPDATE tasks SET is_completed = 0 WHERE id = ? AND user_id = ?",
        (task_id, user_id)
    )

    connection.commit()
    connection.close()

    return redirect("/")


@app.route("/tasks/<int:task_id>/delete", methods=["POST"])
def delete_task(task_id):
    connection = get_connection()
    user_id = get_demo_user_id(connection)

    connection.execute(
        "DELETE FROM tasks WHERE id = ? AND user_id = ?",
        (task_id, user_id)
    )

    connection.commit()
    connection.close()

    return redirect("/")


@app.route("/api/status")
def status():
    return jsonify({
        "status": "ok",
        "message": "Сервер Task Planner работает"
    })


@app.route("/api/tasks")
def list_tasks():
    connection = get_connection()
    user_id = get_demo_user_id(connection)

    tasks = connection.execute("""
        SELECT id, title, description, category, deadline, is_completed
        FROM tasks
        WHERE user_id = ?
        ORDER BY id DESC
    """, (user_id,)).fetchall()

    connection.close()

    return jsonify([dict(task) for task in tasks])


if __name__ == "__main__":
    app.run(debug=True)
