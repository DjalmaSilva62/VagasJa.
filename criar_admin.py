import sqlite3
from werkzeug.security import generate_password_hash

# Conectar ao banco de dados (use o mesmo nome do seu banco real)
conn = sqlite3.connect('seu_banco.db')  # substitua 'seu_banco.db' pelo nome do seu arquivo, como 'banco.db'
cursor = conn.cursor()

# Criar a tabela de administradores, se não existir
cursor.execute('''
CREATE TABLE IF NOT EXISTS admin (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL
)
''')

# Criar o admin inicial (usuário: admin, senha: admin123)
username = 'admin'
password = generate_password_hash('admin123')

# Inserir o administrador (somente se ainda não existir)
try:
    cursor.execute('INSERT INTO admin (username, password) VALUES (?, ?)', (username, password))
    print("Administrador criado com sucesso.")
except sqlite3.IntegrityError:
    print("Administrador já existe.")

conn.commit()
conn.close()
