from flask import Flask, request, render_template, redirect, url_for, send_file, flash, session
import sqlite3
import os
import tempfile
import uuid

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # フラッシュメッセージのためのシークレットキー

DB_FILE = ""
DB_FILE_NAME = ""

@app.route('/')
def index():
    tables = []
    db_name = session.get('db_file_name', "No database loaded")
    db_file = session.get('db_file')

    if db_file and os.path.exists(db_file):
        try:
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cursor.fetchall()]
            conn.close()
        except sqlite3.Error as e:
            tables = []
            db_name = f"Error loading database: {e}"
    return render_template('index.html', tables=tables, sql_query="", db_name=db_name)

@app.route('/load_db', methods=['POST'])
def load_db():
    file = request.files['db_file']
    if file:
        temp_dir = tempfile.gettempdir()
        file_path = os.path.join(temp_dir, f"{uuid.uuid4()}_{file.filename}")
        file.save(file_path)
        session['db_file'] = file_path
        session['db_file_name'] = file.filename
    else:
        flash("No file selected.")
    return redirect(url_for('index'))

@app.route('/create_db', methods=['POST'])
def create_db():
    new_db_name = request.form['new_db_name']
    if not new_db_name:
        flash("Please provide a name for the new database.")
        return redirect(url_for('index'))
    if not new_db_name.endswith(".db"):
        new_db_name += ".db"

    temp_dir = tempfile.gettempdir()
    file_path = os.path.join(temp_dir, f"{uuid.uuid4()}_{new_db_name}")
    conn = sqlite3.connect(file_path)
    conn.close()

    session['db_file'] = file_path
    session['db_file_name'] = new_db_name
    return redirect(url_for('index'))

@app.route('/execute_sql', methods=['POST'])
def execute_sql():
    sql_query = request.form['sql_query']
    result = ""
    columns = []
    db_file = session.get('db_file')

    if not db_file or not os.path.exists(db_file):
        result = "Error: No database loaded or created."
        return render_template('index.html', tables=[], result=result, columns=columns, sql_query=sql_query, db_name=session.get('db_file_name', ''))

    try:
        conn = sqlite3.connect(db_file)
        conn.row_factory = sqlite3.Row  # Use Row factory to access results as dictionaries
        cursor = conn.cursor()
        tables = get_tables()

        # SQL文の判定
        if sql_query.strip().upper().startswith("SELECT"):
            # SELECT文の場合、実行して結果を返す
            cursor.execute(sql_query)
            rows = cursor.fetchall()
            if rows:
                columns = rows[0].keys()
            result = [dict(row) for row in rows]

        else:
            # その他の文（CREATE TABLE, ALTER TABLE, INSERT, UPDATE, DELETEなど）
            cursor.execute(sql_query)
            conn.commit()

            # 影響を与えるテーブル名を推測してデータを表示
            affected_table = None
            for table in tables:
                if table in sql_query:
                    affected_table = table
                    break

            if affected_table:
                # テーブルの全データを取得して表示
                cursor.execute(f"SELECT * FROM {affected_table}")
                rows = cursor.fetchall()
                if rows:
                    columns = rows[0].keys()
                result = [dict(row) for row in rows]
            else:
                result = "Query executed successfully, but no table data to display."

        conn.close()

    except sqlite3.Error as e:
        result = f"An error occurred: {e}"

    return render_template('index.html', tables=get_tables(), result=result, columns=columns, sql_query=sql_query, db_name=session.get('db_file_name', ''))

def get_tables():
    db_file = session.get('db_file')
    if db_file and os.path.exists(db_file):
        try:
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cursor.fetchall()]
            conn.close()
            return tables
        except sqlite3.Error:
            return []
    return []

@app.route('/download_db')
def download_db():
    db_file = session.get('db_file')
    db_file_name = session.get('db_file_name', 'database.db')
    
    if db_file and os.path.exists(db_file):
        return send_file(db_file, as_attachment=True, download_name=db_file_name)
    else:
        flash("No database file available to download.")
        return redirect(url_for('index'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))  # Renderで指定されたポートを取得
    app.run(host='0.0.0.0', port=port, debug=True)  # 0.0.0.0でバインド
