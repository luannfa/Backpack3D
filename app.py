import os
from flask import Flask, render_template, request, redirect, url_for, send_from_directory
from flask import flash
from werkzeug.utils import secure_filename
import sqlite3

app = Flask(__name__)
app.config['SECRET_KEY'] = 'change-me'
app.config['UPLOAD_FOLDER_IMAGES'] = os.path.join('uploads', 'images')
app.config['UPLOAD_FOLDER_FILES'] = os.path.join('uploads', 'files')
app.config['DATABASE'] = 'items.db'

os.makedirs(app.config['UPLOAD_FOLDER_IMAGES'], exist_ok=True)
os.makedirs(app.config['UPLOAD_FOLDER_FILES'], exist_ok=True)

def get_db_connection():
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute(
        """CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            image_filename TEXT,
            file_filename TEXT,
            category TEXT
        )"""
    )
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    search = request.args.get('search', '')
    category = request.args.get('category', '')
    conn = get_db_connection()
    query = 'SELECT * FROM items WHERE 1=1'
    params = []
    if search:
        query += ' AND name LIKE ?'
        params.append(f'%{search}%')
    if category:
        query += ' AND category = ?'
        params.append(category)
    items = conn.execute(query, params).fetchall()
    conn.close()
    categories = get_categories()
    return render_template('index.html', items=items, categories=categories, current_category=category, search=search)

def get_categories():
    conn = get_db_connection()
    rows = conn.execute('SELECT DISTINCT category FROM items').fetchall()
    conn.close()
    return [row['category'] for row in rows if row['category']]

@app.route('/item/new', methods=['GET', 'POST'])
def create_item():
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        category = request.form['category']
        image = request.files['image']
        file = request.files['file']
        image_filename = secure_filename(image.filename) if image else ''
        file_filename = secure_filename(file.filename) if file else ''
        if image_filename:
            image.save(os.path.join(app.config['UPLOAD_FOLDER_IMAGES'], image_filename))
        if file_filename:
            file.save(os.path.join(app.config['UPLOAD_FOLDER_FILES'], file_filename))
        conn = get_db_connection()
        conn.execute(
            'INSERT INTO items (name, description, image_filename, file_filename, category) VALUES (?, ?, ?, ?, ?)',
            (name, description, image_filename, file_filename, category)
        )
        conn.commit()
        conn.close()
        flash('Item criado com sucesso!')
        return redirect(url_for('index'))
    return render_template('form.html', item=None)

@app.route('/item/<int:item_id>/edit', methods=['GET', 'POST'])
def edit_item(item_id):
    conn = get_db_connection()
    item = conn.execute('SELECT * FROM items WHERE id = ?', (item_id,)).fetchone()
    if not item:
        conn.close()
        return 'Item não encontrado', 404
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        category = request.form['category']
        image = request.files['image']
        file = request.files['file']
        image_filename = item['image_filename']
        file_filename = item['file_filename']
        if image and image.filename:
            image_filename = secure_filename(image.filename)
            image.save(os.path.join(app.config['UPLOAD_FOLDER_IMAGES'], image_filename))
        if file and file.filename:
            file_filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER_FILES'], file_filename))
        conn.execute(
            'UPDATE items SET name=?, description=?, image_filename=?, file_filename=?, category=? WHERE id=?',
            (name, description, image_filename, file_filename, category, item_id)
        )
        conn.commit()
        conn.close()
        flash('Item atualizado com sucesso!')
        return redirect(url_for('index'))
    conn.close()
    return render_template('form.html', item=item)

@app.route('/item/<int:item_id>/delete', methods=['POST'])
def delete_item(item_id):
    conn = get_db_connection()
    item = conn.execute('SELECT * FROM items WHERE id = ?', (item_id,)).fetchone()
    if item:
        if item['image_filename']:
            try:
                os.remove(os.path.join(app.config['UPLOAD_FOLDER_IMAGES'], item['image_filename']))
            except FileNotFoundError:
                pass
        if item['file_filename']:
            try:
                os.remove(os.path.join(app.config['UPLOAD_FOLDER_FILES'], item['file_filename']))
            except FileNotFoundError:
                pass
        conn.execute('DELETE FROM items WHERE id = ?', (item_id,))
        conn.commit()
    conn.close()
    flash('Item removido com sucesso!')
    return redirect(url_for('index'))

@app.route('/images/<filename>')
def uploaded_image(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER_IMAGES'], filename)

@app.route('/files/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER_FILES'], filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
