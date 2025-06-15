from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'secreto123'

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///organizador.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Login Manager
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Modelos
class Usuario(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    senha = db.Column(db.String(100), nullable=False)
    tarefas = db.relationship('Tarefa', backref='usuario', lazy=True)

class Tarefa(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    descricao = db.Column(db.Text, nullable=True)
    categoria = db.Column(db.String(50), nullable=True)
    data_hora = db.Column(db.DateTime, nullable=True)
    prioridade = db.Column(db.String(10), default='normal')
    fixada = db.Column(db.Boolean, default=False)
    concluida = db.Column(db.Boolean, default=False)
    criada_em = db.Column(db.DateTime, default=datetime.utcnow)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

# Criação do banco
def criar_banco():
    with app.app_context():
        db.create_all()
        print("Banco criado com sucesso!")

# Rota principal - lista tarefas
@app.route('/')
@login_required
def index():
    tarefas = Tarefa.query.filter_by(usuario_id=current_user.id).order_by(
        Tarefa.fixada.desc(),
        Tarefa.prioridade.desc(),
        Tarefa.data_hora.asc()
    ).all()
    return render_template('index.html', tarefas=tarefas)

# Nova tarefa
@app.route('/nova', methods=['GET', 'POST'])
@login_required
def nova():
    if request.method == 'POST':
        titulo = request.form.get('titulo')
        descricao = request.form.get('descricao')
        categoria = request.form.get('categoria')
        prioridade = request.form.get('prioridade')
        fixada = bool(request.form.get('fixada'))
        data_hora_str = request.form.get('data_hora')
        data_hora = datetime.strptime(data_hora_str, '%Y-%m-%dT%H:%M') if data_hora_str else None

        if not titulo:
            return "Título é obrigatório!", 400

        tarefa = Tarefa(
            titulo=titulo,
            descricao=descricao,
            categoria=categoria,
            prioridade=prioridade or 'normal',
            fixada=fixada,
            data_hora=data_hora,
            usuario_id=current_user.id
        )
        db.session.add(tarefa)
        db.session.commit()
        return redirect(url_for('index'))
    
    return render_template('nova.html')

# Concluir/desmarcar
@app.route('/toggle/<int:id>')
@login_required
def toggle(id):
    tarefa = Tarefa.query.get_or_404(id)
    if tarefa.usuario_id != current_user.id:
        return "Acesso não autorizado", 403
    tarefa.concluida = not tarefa.concluida
    db.session.commit()
    return redirect(url_for('index'))

# Apagar tarefa
@app.route('/delete/<int:id>')
@login_required
def delete(id):
    tarefa = Tarefa.query.get_or_404(id)
    if tarefa.usuario_id != current_user.id:
        return "Acesso não autorizado", 403
    db.session.delete(tarefa)
    db.session.commit()
    return redirect(url_for('index'))

# Rota de registro
@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        senha = generate_password_hash(request.form['senha'])

        if Usuario.query.filter_by(email=email).first():
            flash('E-mail já registrado.', 'error')
            return redirect(url_for('registro'))

        novo_usuario = Usuario(nome=nome, email=email, senha=senha)
        db.session.add(novo_usuario)
        db.session.commit()
        flash('Usuário registrado com sucesso!', 'success')
        return redirect(url_for('login'))
    
    return render_template('registro.html')

# Rota de login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']

        usuario = Usuario.query.filter_by(email=email).first()
        if usuario and check_password_hash(usuario.senha, senha):
            login_user(usuario)
            flash('Login realizado com sucesso!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Credenciais inválidas', 'error')
            return redirect(url_for('login'))
    
    return render_template('login.html')

# Logout
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Sessão encerrada com sucesso.', 'success')
    return redirect(url_for('login'))

# Iniciar app
if __name__ == '__main__':
    criar_banco()
    app.run(debug=True)
