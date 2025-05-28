from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_required, login_user, logout_user, current_user, UserMixin
from werkzeug.utils import secure_filename
import os
import sqlite3
from functools import wraps


app = Flask(__name__)
app.secret_key = 'chave-secreta-muito-forte'

# Configuração do banco de dados
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Limite de 16MB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///banco.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Configuração do Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login_candidato'

# Modelos
class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    senha = db.Column(db.String(100), nullable=False)
    tipo = db.Column(db.String(20), nullable=False)

class Vaga(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(120), nullable=False)
    descricao = db.Column(db.Text, nullable=False)
    empresa_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)

class Curriculo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    cidade = db.Column(db.String(100))
    telefone = db.Column(db.String(20))
    nascimento = db.Column(db.String(20))
    arquivo = db.Column(db.String(200))
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)

class Candidatura(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    vaga_id = db.Column(db.Integer, db.ForeignKey('vaga.id'), nullable=False)

class Candidato(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    senha = db.Column(db.String(100))

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect('banco.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM admin WHERE username = ?", (username,))
        admin = cursor.fetchone()
        conn.close()

        if admin and check_password_hash(admin[2], password):
            session['admin_logged_in'] = True
            session['admin_username'] = admin[1]
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Usuário ou senha incorretos')

    return render_template('admin_login.html')

@login_manager.user_loader
def load_user(user_id):
    return Candidato.query.get(int(user_id))

def login_admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    return render_template('admin_dashboard.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    session.pop('admin_username', None)
    return redirect(url_for('admin_login'))

# Rotas
@app.route('/')
def index():
    vagas = Vaga.query.all()
    return render_template('index.html', vagas=vagas)

# Login antigo (session-based)
@app.route('/login_sistema', methods=['GET', 'POST'])  # renomeei a rota
def login_sistema():
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['password']
        usuario = Usuario.query.filter_by(email=email, senha=senha).first()
        if usuario:
            session['usuario_id'] = usuario.id
            session['tipo'] = usuario.tipo
            return redirect(url_for('dashboard'))
        else:
            return "Email ou senha incorretos!"
    return render_template('login.html')

# Login com Flask-Login (Candidato)
@app.route('/login/candidato', methods=['GET', 'POST'])  # rota nova e nome único
def login_candidato():
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']
        user = Candidato.query.filter_by(email=email, senha=senha).first()
        if user:
            login_user(user)
            return redirect(url_for('dashboard_candidato'))
        else:
            return "Usuário ou senha inválidos"
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    logout_user()
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['password']
        tipo = request.form['tipo']
        novo_usuario = Usuario(email=email, senha=senha, tipo=tipo)
        db.session.add(novo_usuario)
        db.session.commit()
        return redirect(url_for('login_sistema'))
    return render_template('register.html')

@app.route('/empresa/vagas')
def empresa_vagas():
    if 'usuario_id' not in session:
        return redirect(url_for('login_sistema'))
    if session.get('tipo') != 'empresa':
        return "Acesso restrito para empresas."
    return "Página de gerenciamento de vagas da empresa."

@app.route('/dashboard')
def dashboard():
    if 'usuario_id' not in session:
        return redirect(url_for('login_sistema'))
    if session['tipo'] == 'empresa':
        return render_template('dashboard_empresa.html')
    elif session['tipo'] == 'candidato':
        return render_template('dashboard_candidato.html')

@app.route('/empresa/vagas/nova', methods=['GET', 'POST'])
def nova_vaga():
    if 'usuario_id' not in session or session.get('tipo') != 'empresa':
        return redirect(url_for('login_sistema'))
    if request.method == 'POST':
        titulo = request.form['titulo']
        descricao = request.form['descricao']
        nova = Vaga(titulo=titulo, descricao=descricao, empresa_id=session['usuario_id'])
        db.session.add(nova)
        db.session.commit()
        return redirect(url_for('minhas_vagas'))
    return render_template('nova_vaga.html')

@app.route('/empresa/vagas/minhas')
def minhas_vagas():
    if 'usuario_id' not in session or session.get('tipo') != 'empresa':
        return redirect(url_for('login_sistema'))
    vagas = Vaga.query.filter_by(empresa_id=session['usuario_id']).all()
    return render_template('minhas_vagas.html', vagas=vagas)

@app.route('/candidato/curriculo', methods=['GET', 'POST'])
def candidato_curriculo():
    if 'usuario_id' not in session or session.get('tipo') != 'candidato':
        return redirect(url_for('login_sistema'))
    if request.method == 'POST':
        nome = request.form['nome']
        cidade = request.form['cidade']
        telefone = request.form['telefone']
        nascimento = request.form['nascimento']
        curriculo = request.files['arquivo']
        foto = request.files['foto']
        caminho_curriculo = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(curriculo.filename))
        caminho_foto = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(foto.filename))
        curriculo.save(caminho_curriculo)
        foto.save(caminho_foto)
        novo_curriculo = Curriculo(
            nome=nome,
            cidade=cidade,
            telefone=telefone,
            nascimento=nascimento,
            arquivo=caminho_curriculo,
            usuario_id=session['usuario_id']
        )
        db.session.add(novo_curriculo)
        db.session.commit()
        return "Currículo enviado com sucesso!"
    return render_template('dashboard_candidato.html')

@app.route('/empresa/perfil', methods=['POST'])
def empresa_perfil():
    if 'usuario_id' not in session or session.get('tipo') != 'empresa':
        return redirect(url_for('login_sistema'))
    nome = request.form['nome']
    cidade = request.form['cidade']
    logo = request.files['logo']
    caminho_logo = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(logo.filename))
    logo.save(caminho_logo)
    return "Perfil da empresa atualizado!"

@app.route('/empresa/vagas', methods=['POST'])
def publicar_vaga():
    if 'usuario_id' not in session or session.get('tipo') != 'empresa':
        return redirect(url_for('login_sistema'))
    titulo = request.form['titulo']
    descricao = request.form['descricao']
    nova_vaga = Vaga(titulo=titulo, descricao=descricao, empresa_id=session['usuario_id'])
    db.session.add(nova_vaga)
    db.session.commit()
    return "Vaga publicada com sucesso!"

@app.route('/vaga/<int:vaga_id>')
def ver_vaga(vaga_id):
    vaga = Vaga.query.get_or_404(vaga_id)
    return render_template('vaga_detalhes.html', vaga=vaga)

@app.route('/candidato/vagas')
@login_required
def vagas_candidato():
    vagas = Vaga.query.all()
    return render_template('vagas_candidato.html', vagas=vagas)

@app.route('/dashboard/candidato')
@login_required
def dashboard_candidato():
    return render_template('dashboard_candidato.html', usuario=current_user)

@app.route('/admin_dashboard')
@login_admin_required
def admin_dashboard_full():
    conn = sqlite3.connect('seu_banco.db')
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM candidatos')
    candidatos = cursor.fetchall()

    cursor.execute('SELECT * FROM empresas')
    empresas = cursor.fetchall()

    cursor.execute('SELECT * FROM vagas')
    vagas = cursor.fetchall()

    conn.close()

    return render_template('admin_dashboard.html', candidatos=candidatos, empresas=empresas, vagas=vagas)

@app.route('/admin/remover_candidato/<int:id>')
@login_admin_required
def remover_candidato(id):
    conn = sqlite3.connect('seu_banco.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM candidatos WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    flash("Candidato removido com sucesso", "success")
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/remover_empresa/<int:id>')
@login_admin_required
def remover_empresa(id):
    conn = sqlite3.connect('seu_banco.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM empresas WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    flash("Empresa removida com sucesso", "success")
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/remover_vaga/<int:id>')
@login_admin_required
def remover_vaga(id):
    conn = sqlite3.connect('seu_banco.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM vagas WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    flash("Vaga removida com sucesso", "success")
    return redirect(url_for('admin_dashboard'))

@app.route('/vaga/<int:vaga_id>/candidatar', methods=['POST'])
@login_required
def candidatar_vaga(vaga_id):
    vaga = Vaga.query.get_or_404(vaga_id)
    candidatura_existente = Candidatura.query.filter_by(usuario_id=current_user.id, vaga_id=vaga_id).first()

    if candidatura_existente:
        flash("Você já se candidatou a esta vaga.", "warning")
    else:
        nova_candidatura = Candidatura(usuario_id=current_user.id, vaga_id=vaga_id)
        db.session.add(nova_candidatura)
        db.session.commit()
        flash("Candidatura realizada com sucesso!", "success")

    return redirect(url_for('ver_vaga', vaga_id=vaga_id))




# Executa o app
if __name__ == '__main__':
    app.run(debug=True)
