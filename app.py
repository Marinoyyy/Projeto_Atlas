import pandas as pd
import json
import os
import time
from unidecode import unidecode
from flask import Flask, jsonify, render_template, request, url_for, redirect, send_from_directory, flash
from datetime import datetime
import traceback
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.types import JSON
from functools import wraps

# Carrega as variáveis de ambiente
load_dotenv()

# --- INICIALIZAÇÃO E CONFIGURAÇÃO ---
app = Flask(__name__)
app.secret_key = os.getenv("CLIENT_SECRET", "uma-chave-secreta-forte-e-diferente")

# Configuração do SQLAlchemy a partir da variável de ambiente DATABASE_URL
# Para desenvolvimento local, ele usará um arquivo sqlite. No OnRender, usará o PostgreSQL.
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///super_carometro.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# --- CONFIGURAÇÃO DO CLOUDINARY ---
cloudinary.config(
    cloud_name=os.getenv('CLOUD_NAME'),
    api_key=os.getenv('API_KEY'),
    api_secret=os.getenv('API_SECRET')
)

# --- CONSTANTES GLOBAIS (sem alterações) ---
ESTRUTURA_ATRIBUTOS = {
    'Tecnica': ['Uso do Sistema', 'Ferramentas', 'Maestria no setor', 'Conhecimento do processo', 'Somos Inquietos'],
    'Agilidade': ['Velocidade de entrega', 'Ritmo de Execução', 'Somos apaixonados pela execução', 'Pró-atividade'],
    'Comportamento': ['Engajamento', 'Relacionamento-interpessoal', 'Influencia no time', 'nutrimos nossas relações'],
    'Adaptabilidade': ['apoio', 'Resolução de problemas', 'Resiliencia', 'Flexibilidade'],
    'Qualidade': ['buscamos o sucesso responsável', 'fazemos os olhos dos nossos clientes brilharem', 'Qualidade', 'Segurança', 'Foco'],
    'Regularidade': ['Absenteísmo', 'Regularidade']
}
ICON_MAP = {
    'Tecnica': 'fa-solid fa-gears', 'Agilidade': 'fa-solid fa-bolt-lightning', 'Comportamento': 'fa-solid fa-handshake-angle',
    'Adaptabilidade': 'fa-solid fa-shuffle', 'Qualidade': 'fa-solid fa-gem', 'Regularidade': 'fa-solid fa-calendar-check'
}
PESOS = {
    'Picking':       {'Tecnica': 3, 'Agilidade': 5, 'Comportamento': 4, 'Adaptabilidade': 3, 'Qualidade': 3, 'Regularidade': 4},
    'Checkout':      {'Tecnica': 3, 'Agilidade': 5, 'Comportamento': 4, 'Adaptabilidade': 3, 'Qualidade': 5, 'Regularidade': 4},
    'Expedicao':     {'Tecnica': 2, 'Agilidade': 4, 'Comportamento': 4, 'Adaptabilidade': 2, 'Qualidade': 4, 'Regularidade': 4},
    'Loja':          {'Tecnica': 3, 'Agilidade': 3, 'Comportamento': 4, 'Adaptabilidade': 3, 'Qualidade': 4, 'Regularidade': 4},
    'Reabastecimento':{'Tecnica': 4, 'Agilidade': 4, 'Comportamento': 4, 'Adaptabilidade': 4, 'Qualidade': 5, 'Regularidade': 4},
    'Controle de Estoque':{'Tecnica': 5, 'Agilidade': 2, 'Comportamento': 4, 'Adaptabilidade': 5, 'Qualidade': 5, 'Regularidade': 4},
    'Recebimento':   {'Tecnica': 4, 'Agilidade': 3, 'Comportamento': 4, 'Adaptabilidade': 4, 'Qualidade': 5, 'Regularidade': 4},
    'DEFAULT':       {'Tecnica': 1, 'Agilidade': 1, 'Comportamento': 1, 'Adaptabilidade': 1, 'Qualidade': 1, 'Regularidade': 1}
}
INSIGNIAS_DISPONIVEIS = {
    "precisao": {"icone": "fa-solid fa-crosshairs", "titulo": "Precisão", "descricao": "Executa tarefas com altíssimo nível de acerto, minimizando erros."},
    "velocista": {"icone": "fa-solid fa-person-running", "titulo": "Velocista", "descricao": "Possui um ritmo de execução consistentemente acima da média."},
    "guardiao": {"icone": "fa-solid fa-shield-halved", "titulo": "Guardião da Qualidade", "descricao": "Zela pelos padrões de qualidade, garantindo a excelência na entrega."},
    "organizador": {"icone": "fa-solid fa-sitemap", "titulo": "Organizador", "descricao": "Mantém o ambiente de trabalho e os processos sempre organizados."},
    "resolvedor": {"icone": "fa-solid fa-check-to-slot", "titulo": "Resolvedor", "descricao": "Encontra soluções criativas e eficazes para problemas complexos."},
    "mentor": {"icone": "fa-solid fa-chalkboard-user", "titulo": "Mentor", "descricao": "Ajuda ativamente no desenvolvimento e no suporte de outros colegas."},
    "autodidata": {"icone": "fa-solid fa-robot", "titulo": "Autodidata", "descricao": "Busca constantemente aprender e se aprimorar de forma independente."},
    "comunicador": {"icone": "fa-solid fa-comments", "titulo": "Comunicador", "descricao": "Possui habilidades excepcionais de comunicação e relacionamento."},
    "inovador": {"icone": "fa-solid fa-lightbulb", "titulo": "Inovador", "descricao": "Propõe novas ideias e melhorias para os processos existentes."},
    "polivalente": {"icone": "fa-solid fa-star", "titulo": "Polivalente", "descricao": "Adapta-se com facilidade a diferentes funções e desafios."},
    "consistencia": {"icone": "fa-solid fa-calendar-check", "titulo": "Consistência", "descricao": "Exemplo de regularidade, presença e pontualidade."}
}

# --- DECORADOR DE PERMISSÃO ---
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.email != 'pedro.pereira@grupoboticario.com.br': # <--- LINHA ALTERADA
            flash("Acesso não autorizado a esta área.", "danger")
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

# --- MODELOS DO BANCO DE DADOS (SQLALCHEMY) ---

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    cargo = db.Column(db.String(100))
    password = db.Column(db.String(255), nullable=False)
    force_password_reset = db.Column(db.Boolean, default=False)

class Colaborador(db.Model):
    __tablename__ = 'colaboradores'
    id = db.Column(db.Integer, primary_key=True)
    nome_completo = db.Column(db.String(200), unique=True, nullable=False)
    cargo = db.Column(db.String(100))
    processo = db.Column(db.String(100))
    turno = db.Column(db.String(50))
    turno_num = db.Column(db.Integer)
    nome_gestor_imediato = db.Column(db.String(200))
    foto_url = db.Column(db.String(500))
    
    # Relacionamentos
    avaliacoes = db.relationship('Avaliacao', backref='colaborador', lazy=True, cascade="all, delete-orphan")
    insignias = db.relationship('Insignia', backref='colaborador', lazy=True, cascade="all, delete-orphan")
    pd_itens = db.relationship('PDI', backref='colaborador', lazy=True, cascade="all, delete-orphan")
    historico_avaliacoes = db.relationship('Historico', backref='colaborador', lazy=True, cascade="all, delete-orphan")

class Avaliacao(db.Model):
    __tablename__ = 'avaliacoes'
    id = db.Column(db.Integer, primary_key=True)
    colaborador_id = db.Column(db.Integer, db.ForeignKey('colaboradores.id'), nullable=False)
    atributos = db.Column(JSON)

class Insignia(db.Model):
    __tablename__ = 'insignias'
    id = db.Column(db.Integer, primary_key=True)
    colaborador_id = db.Column(db.Integer, db.ForeignKey('colaboradores.id'), nullable=False)
    insignia_id = db.Column(db.String(50), nullable=False)

class PDI(db.Model):
    __tablename__ = 'pdi'
    id = db.Column(db.Integer, primary_key=True)
    colaborador_id = db.Column(db.Integer, db.ForeignKey('colaboradores.id'), nullable=False)
    descricao = db.Column(db.Text, nullable=False)
    prazo = db.Column(db.String(20))
    status = db.Column(db.String(50), default='A Fazer')

class Historico(db.Model):
    __tablename__ = 'historico'
    id = db.Column(db.Integer, primary_key=True)
    colaborador_id = db.Column(db.Integer, db.ForeignKey('colaboradores.id'), nullable=False)
    data = db.Column(db.DateTime, default=datetime.utcnow)
    overall = db.Column(db.Integer)
    sub_atributos = db.Column(JSON)

# --- FUNÇÕES AUXILIARES DE UTILIZADORES ---
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- FUNÇÕES DE CÁLCULO (sem alterações) ---
def calcular_overall_com_notas(notas_sub_atributos, processo_colaborador):
    medias_principais = {}
    for attr_principal, sub_attrs in ESTRUTURA_ATRIBUTOS.items():
        soma_sub = sum(notas_sub_atributos.get(sub, 50) for sub in sub_attrs)
        media = round(soma_sub / len(sub_attrs)) if sub_attrs else 50
        medias_principais[attr_principal] = media
    setor = str(processo_colaborador).upper() if isinstance(processo_colaborador, str) and processo_colaborador.strip() else 'DEFAULT'
    pesos_upper = {k.upper(): v for k, v in PESOS.items()}
    pesos_setor = pesos_upper.get(setor, pesos_upper.get('DEFAULT'))
    numerador = sum(medias_principais.get(k, 50) * v for k, v in pesos_setor.items())
    denominador = sum(pesos_setor.values())
    return round(numerador / denominador) if denominador > 0 else 50

def calcular_overall_individual(colaborador_dict, pesos_gerais):
    medias_principais = {item['nome_principal']: item['valor_principal'] for item in colaborador_dict['atributos_detalhados']}
    processo_colaborador = colaborador_dict.get('processo')
    setor_atual = str(processo_colaborador).upper() if isinstance(processo_colaborador, str) and processo_colaborador.strip() else 'DEFAULT'
    pesos_upper = {k.upper(): v for k, v in pesos_gerais.items()}
    pesos_setor = pesos_upper.get(setor_atual, pesos_upper.get('DEFAULT'))
    numerador = sum(medias_principais.get(k, 50) * v for k, v in pesos_setor.items())
    denominador = sum(pesos_setor.values())
    return round(numerador / denominador) if denominador > 0 else 50

def get_cor_por_pontuacao(pontuacao):
    if pontuacao >= 80: return '#28a745'
    if pontuacao >= 60: return '#ffc107'
    return '#dc3545'
    
def converter_score_para_estrelas(score):
    if score >= 90: return 5
    if score >= 80: return 4
    if score >= 70: return 3
    if score >= 60: return 2
    if score > 0: return 1
    return 0
    
# --- FUNÇÃO PRINCIPAL DE BUSCA DE DADOS ---
def get_dados_completos():
    colaboradores_db = Colaborador.query.filter(Colaborador.processo != 'Desligado').all()
    colaboradores_list = []

    for c in colaboradores_db:
        colaborador_dict = {
            'id': c.id,
            'Nome_completo': c.nome_completo,
            'Cargo': c.cargo,
            'Processo': c.processo,
            'Turno': c.turno,
            'Turno_Num': c.turno_num,
            'Nome_Gestor_Imediato': c.nome_gestor_imediato
        }

        if c.foto_url and c.foto_url.strip():
            colaborador_dict['foto'] = c.foto_url
        else:
            nome_formatado = unidecode(c.nome_completo).replace(' ', '+')
            colaborador_dict['foto'] = f"https://ui-avatars.com/api/?name={nome_formatado}&background=cccccc&color=000000&size=150"

        avaliacao = Avaliacao.query.filter_by(colaborador_id=c.id).first()
        notas_sub_atributos = avaliacao.atributos if avaliacao and avaliacao.atributos else {}
        
        colaborador_dict['atributos_detalhados'] = []
        for attr_principal, sub_attrs in ESTRUTURA_ATRIBUTOS.items():
            soma_sub = sum(int(notas_sub_atributos.get(sub, 50)) for sub in sub_attrs)
            media = round(soma_sub / len(sub_attrs)) if sub_attrs else 50
            colaborador_dict['atributos_detalhados'].append({
                'nome_principal': attr_principal, 'valor_principal': media, 'cor': get_cor_por_pontuacao(media),
                'icone': ICON_MAP.get(attr_principal, ''), 'sub_atributos': [{'nome': sub, 'valor': int(notas_sub_atributos.get(sub, 50))} for sub in sub_attrs]
            })

        insignias_db = Insignia.query.filter_by(colaborador_id=c.id).all()
        colaborador_dict['insignias'] = [i.insignia_id for i in insignias_db]

        pdi_db = PDI.query.filter_by(colaborador_id=c.id).all()
        colaborador_dict['pdi'] = [{'id': p.id, 'descricao': p.descricao, 'prazo': p.prazo, 'status': p.status} for p in pdi_db]
        
        colaboradores_list.append(colaborador_dict)

    return colaboradores_list

# --- ROTAS DE AUTENTICAÇÃO ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))

    if request.method == 'POST':
        email = request.form.get('email', '').lower()
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()

        if not user or not check_password_hash(user.password, password):
            flash('Email ou password incorretos.', 'danger')
            return redirect(url_for('login'))
        
        login_user(user)
        
        if user.force_password_reset:
            flash('Este é o seu primeiro acesso. Por favor, defina uma nova senha.', 'info')
            return redirect(url_for('force_reset_password'))
        
        return redirect(url_for('home'))

    return render_template('login.html')

@app.route('/force-reset-password', methods=['GET', 'POST'])
@login_required
def force_reset_password():
    if not current_user.force_password_reset:
        return redirect(url_for('home')) 

    if request.method == 'POST':
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        if not new_password or new_password != confirm_password:
            flash('As passwords não coincidem ou estão em branco.', 'danger')
            return redirect(url_for('force_reset_password'))
        
        user = User.query.get(current_user.id)
        if user:
            user.password = generate_password_hash(new_password, method='pbkdf2:sha256')
            user.force_password_reset = False
            db.session.commit()
            flash('Password redefinida com sucesso! Pode continuar.', 'success')
            return redirect(url_for('home'))

    return render_template('force_reset_password.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# --- ROTAS DA APLICAÇÃO ---
# --- ROTAS DA ÁREA DE ADMINISTRAÇÃO (DEV) ---

@app.route('/dev')
@login_required
@admin_required
def dev_dashboard():
    all_users = User.query.order_by(User.nome).all()
    return render_template('dev_dashboard.html', users=all_users)

@app.route('/dev/create_user', methods=['GET', 'POST'])
@login_required
@admin_required
def dev_create_user():
    if request.method == 'POST':
        email = request.form.get('email', '').lower()
        temp_password = request.form.get('temp_password')

        if not email or not temp_password:
            flash("Email e senha temporária são obrigatórios.", "danger")
            return redirect(url_for('dev_create_user'))

        # Procura o utilizador no banco de dados primeiro
        if User.query.filter_by(email=email).first():
            flash(f"O email '{email}' já está registado no sistema.", "danger")
            return redirect(url_for('dev_create_user'))

        # Procura na planilha para obter nome e cargo
        try:
            df = pd.read_excel('Colaboradores.xlsx')
            df['E-mail'] = df['E-mail'].str.lower()
            colaborador_info = df[df['E-mail'] == email].to_dict('records')
            if not colaborador_info:
                flash(f"Email '{email}' não encontrado na planilha de Colaboradores.", "danger")
                return redirect(url_for('dev_create_user'))
            
            info = colaborador_info[0]
            password_hash = generate_password_hash(temp_password, method='pbkdf2:sha256')
            
            new_user = User(
                nome=info.get('Nome_completo'),
                email=email,
                cargo=info.get('Cargo'),
                password=password_hash,
                force_password_reset=True
            )
            db.session.add(new_user)
            db.session.commit()
            flash(f"Utilizador '{info.get('Nome_completo')}' criado com sucesso!", "success")
            return redirect(url_for('dev_dashboard'))

        except Exception as e:
            flash(f"Ocorreu um erro: {e}", "danger")
            return redirect(url_for('dev_create_user'))
            
    return render_template('dev_create_user.html')

@app.route('/dev/delete_user/<int:user_id>')
@login_required
@admin_required
def dev_delete_user(user_id):
    if user_id == current_user.id:
        flash("Não pode apagar o seu próprio utilizador.", "danger")
        return redirect(url_for('dev_dashboard'))
        
    user_to_delete = User.query.get_or_404(user_id)
    db.session.delete(user_to_delete)
    db.session.commit()
    flash(f"Utilizador '{user_to_delete.nome}' apagado com sucesso.", "success")
    return redirect(url_for('dev_dashboard'))

@app.route('/dev/download_consolidado')
@login_required
@admin_required
def download_consolidado():
    try:
        # Pega os dados mais recentes do banco de dados
        colaboradores = Colaborador.query.all()
        df_colaboradores = pd.DataFrame([(c.nome_completo, c.cargo, c.processo, c.turno) for c in colaboradores], columns=['Nome_completo', 'Cargo', 'Processo', 'Turno'])
        
        avaliacoes = Avaliacao.query.all()
        if avaliacoes:
            dict_avaliacoes = {a.colaborador.nome_completo: a.atributos for a in avaliacoes if a.colaborador}
            df_avaliacoes = pd.DataFrame.from_dict(dict_avaliacoes, orient='index')
            df_avaliacoes.reset_index(inplace=True)
            df_avaliacoes.rename(columns={'index': 'Nome_completo'}, inplace=True)
            
            # Junta os dataframes
            df_final = pd.merge(df_colaboradores, df_avaliacoes, on='Nome_completo', how='left')
        else:
            df_final = df_colaboradores

        nome_ficheiro_saida = 'Colaboradores_Consolidado.xlsx'
        df_final.to_excel(nome_ficheiro_saida, index=False)

        return send_from_directory(directory='.', path=nome_ficheiro_saida, as_attachment=True)

    except Exception as e:
        print(f"ERRO AO GERAR RELATÓRIO: {e}")
        traceback.print_exc()
        return "Ocorreu um erro interno ao gerar o relatório.", 500

@app.route('/')
@login_required
def home():
    return redirect(url_for('dashboard_setores'))

@app.route('/minha_equipa')
@login_required
def minha_equipa():
    colaboradores_todos = get_dados_completos()
    
    liderados_nomes = {c.nome_completo for c in Colaborador.query.filter_by(nome_gestor_imediato=current_user.nome).all()}
    
    minha_equipa_completa = [c for c in colaboradores_todos if c['Nome_completo'] in liderados_nomes]

    for membro in minha_equipa_completa:
        membro['overall'] = calcular_overall_individual(membro, PESOS)

    return render_template('minha_equipa.html', equipa=minha_equipa_completa, get_cor_por_pontuacao=get_cor_por_pontuacao)

@app.route('/dashboard')
@login_required
def dashboard_setores():
    colaboradores = get_dados_completos()
    
    colaboradores_operacionais = [c for c in colaboradores if c.get('Cargo') in ['Operacional', 'Op Empilhadeira']]
    setores_info = []
    config_setores = {
        'Picking': {'icone': 'fa-solid fa-cart-shopping', 'cor': '#011E38'}, 'Checkout': {'icone': 'fa-solid fa-cash-register', 'cor': '#011E38'},
        'Expedicao': {'icone': 'fa-solid fa-truck-fast', 'cor': '#011E38'}, 'Recebimento': {'icone': 'fa-solid fa-boxes-packing', 'cor': '#011E38'},
        'Reabastecimento': {'icone': 'fa-solid fa-warehouse', 'cor': '#011E38'}, 'Controle de Estoque': {'icone': 'fa-solid fa-clipboard-list', 'cor': '#011E38'},
        'Loja': {'icone': 'fa-solid fa-store', 'cor': '#011E38'}, 'DEFAULT': {'icone': 'fa-solid fa-question-circle', 'cor': '#6c757d'}
    }

    setores_contagem = pd.Series([c.get('Processo') for c in colaboradores_operacionais]).value_counts().to_dict()

    for setor, contagem in setores_contagem.items():
        if setor not in config_setores: continue
        setores_info.append({
            "nome": setor, "contagem": contagem, "tipo": "processo", 
            **config_setores.get(setor, config_setores['DEFAULT'])
        })

    if current_user.cargo in ["Coordenador - Log", "Gerente"]:
        cargos_administrativos = ["Coordenador - Log", "Analista Log I", "Analista Log II", "Assistente Administrativo", "Especialista"]
        contagem_admin = sum(1 for c in colaboradores if c.get('Cargo') in cargos_administrativos)
        setores_info.append({
            "nome": "Administrativos", "contagem": contagem_admin, 
            "icone": "fa-solid fa-user-tie", "cor": "#011E38", "tipo": "cargo"
        })

        cargos_tecnicos = ["Técnico III - Log", "Assistente"]
        contagem_tecnico = sum(1 for c in colaboradores if c.get('Cargo') in cargos_tecnicos)
        setores_info.append({
            "nome": "Técnicos", "contagem": contagem_tecnico, 
            "icone": "fa-solid fa-helmet-safety", "cor": "#011E38", "tipo": "cargo"
        })

    is_leader = Colaborador.query.filter_by(nome_gestor_imediato=current_user.nome).first() is not None
    return render_template('dashboard.html', setores=sorted(setores_info, key=lambda x: x['nome']), is_leader=is_leader)

@app.route('/setor/<nome_setor>')
@login_required
def selecao_turno(nome_setor):
    return render_template('selecao_turno.html', nome_setor=nome_setor)

@app.route('/setor/<nome_setor>/turno/<int:num_turno>')
@login_required
def grid_colaboradores(nome_setor, num_turno):
    colaboradores = get_dados_completos()
    equipe_filtrada = [
        c for c in colaboradores 
        if c.get('Processo') == nome_setor 
        and c.get('Turno_Num') == num_turno
        and c.get('Cargo') in ['Operacional', 'Op Empilhadeira']
    ]
    liderados = Colaborador.query.filter_by(nome_gestor_imediato=current_user.nome).first() is not None
    role = 'lider' if liderados else 'visualizador'
    
    return render_template('setor_grid.html', equipe=equipe_filtrada, nome_setor=nome_setor, num_turno=num_turno, role=role)

@app.route('/colaborador/<int:colaborador_id>')
@login_required
def detalhe_colaborador(colaborador_id):
    colaborador = next((c for c in get_dados_completos() if c['id'] == colaborador_id), None)
    if not colaborador: return "Colaborador não encontrado", 404
    
    pode_editar = (colaborador.get('Nome_Gestor_Imediato') == current_user.nome)
    role = 'lider' if pode_editar else 'visualizador'
    
    overall = calcular_overall_individual(colaborador, PESOS)
    overall_cor = get_cor_por_pontuacao(overall)
    
    overalls_preview = []
    medias_principais = {item['nome_principal']: item['valor_principal'] for item in colaborador['atributos_detalhados']}
    
    for setor, pesos_setor in PESOS.items():
        if setor != 'DEFAULT' and setor != colaborador.get('Processo'):
            numerador = sum(medias_principais.get(k, 50) * v for k, v in pesos_setor.items())
            denominador = sum(pesos_setor.values())
            overall_simulado = round(numerador / denominador) if denominador > 0 else 50
            overalls_preview.append({'setor': setor, 'overall': overall_simulado})
    overalls_preview = sorted(overalls_preview, key=lambda x: x['overall'], reverse=True)

    return render_template(
        'colaborador_detalhe.html', 
        colaborador=colaborador, 
        overall=overall, 
        overall_cor=overall_cor, 
        role=role, 
        pode_editar=pode_editar,
        insignias_disponiveis=INSIGNIAS_DISPONIVEIS,
        overalls_preview=overalls_preview,
        get_cor_por_pontuacao=get_cor_por_pontuacao
    )

@app.route('/adicionar_colaborador', methods=['GET', 'POST'])
@login_required
def adicionar_colaborador():
    if request.method == 'POST':
        try:
            nome_completo = request.form.get('nome_completo').strip()
            
            colaborador = Colaborador.query.filter_by(nome_completo=nome_completo).first()
            if not colaborador:
                colaborador = Colaborador(nome_completo=nome_completo)
                db.session.add(colaborador)

            colaborador.cargo = request.form.get('cargo')
            colaborador.processo = request.form.get('processo')
            colaborador.turno = request.form.get('turno')
            colaborador.nome_gestor_imediato = request.form.get('lider')

            try:
                colaborador.turno_num = int(colaborador.turno.split('º')[0])
            except (ValueError, IndexError):
                colaborador.turno_num = None
            
            foto = request.files.get('foto')
            if foto and foto.filename != '':
                nome_base = unidecode(nome_completo.lower().replace(' ', '-'))
                upload_result = cloudinary.uploader.upload(
                    foto, public_id=nome_base, overwrite=True, unique_filename=False
                )
                colaborador.foto_url = upload_result.get('secure_url')
            
            db.session.commit()
            flash(f'Colaborador {nome_completo} salvo com sucesso!', 'success')
            return redirect(url_for('home'))
        except Exception as e:
            db.session.rollback()
            print(f"ERRO AO ADICIONAR/ATUALIZAR COLABORADOR: {e}")
            traceback.print_exc()
            flash("Ocorreu um erro ao salvar o colaborador.", 'danger')

    setores = [setor for setor in PESOS.keys() if setor != 'DEFAULT']
    return render_template('adicionar_colaborador.html', setores=setores)

@app.route('/colaborador/<int:colaborador_id>/mudar_setor', methods=['GET', 'POST'])
@login_required
def mudar_setor(colaborador_id):
    colaborador = Colaborador.query.get_or_404(colaborador_id)
    
    if request.method == 'POST':
        novo_setor = request.form.get('novo_setor')
        colaborador.processo = novo_setor
        db.session.commit()
        flash(f'Setor de {colaborador.nome_completo} alterado para {novo_setor}.', 'success')
        return redirect(url_for('detalhe_colaborador', colaborador_id=colaborador.id))

    todos_setores = [setor for setor in PESOS.keys() if setor != 'DEFAULT']
    todos_setores.append("Desligado")
    
    colaborador_dict = {
        'id': colaborador.id,
        'Nome_completo': colaborador.nome_completo,
        'Processo': colaborador.processo
    }
    return render_template('mudar_setor.html', colaborador=colaborador_dict, todos_setores=todos_setores)

@app.route('/detalhamento')
@login_required
def detalhamento_geral():
    colaboradores = get_dados_completos()
    for c in colaboradores:
        # O 'overall' é uma média geral, para a matriz precisamos do overall específico do processo atual
        c['overall'] = calcular_overall_individual(c, PESOS)
    
    colaboradores_operacionais = [c for c in colaboradores if c.get('Cargo') in ['Operacional', 'Op Empilhadeira']]

    dados_agrupados = {}
    for c in colaboradores_operacionais:
        turno = c.get('Turno', 'N/A')
        processo = c.get('Processo', 'N/A')
        if turno not in dados_agrupados: dados_agrupados[turno] = {}
        if processo not in dados_agrupados[turno]: dados_agrupados[turno][processo] = []
        dados_agrupados[turno][processo].append(c)
        
    stats_times = {}
    for turno, processos in dados_agrupados.items():
        if turno not in stats_times: stats_times[turno] = []
        for processo, membros in processos.items():
            membros_ordenados = sorted(membros, key=lambda x: x['overall'], reverse=True)
            dados_agrupados[turno][processo] = membros_ordenados
            media_overall_time = sum(m['overall'] for m in membros) / len(membros) if membros else 0
            estrelas_time = converter_score_para_estrelas(media_overall_time)
            stats_times[turno].append({'nome_setor': processo, 'media_overall': round(media_overall_time), 'estrelas': estrelas_time})
        stats_times[turno] = sorted(stats_times[turno], key=lambda x: x['media_overall'], reverse=True)
        
    return render_template('detalhamento_geral.html', dados_agrupados=dados_agrupados, stats_times=stats_times)
# --- ROTAS DE API (Atualizadas para o DB) ---
@app.route('/api/salvar_avaliacao', methods=['POST'])
@login_required
def salvar_avaliacao_api():
    dados = request.json
    nome_colaborador = dados.get('nome_completo')
    processo_colaborador = dados.get('processo')
    sub_atributos_recebidos = dados.get('sub_atributos', {})

    # --- LINHA CORRIGIDA ---
    # Converte todos os valores recebidos para inteiros
    notas_numericas = {chave: int(valor) for chave, valor in sub_atributos_recebidos.items()}

    colaborador = Colaborador.query.filter_by(nome_completo=nome_colaborador).first()
    if not colaborador:
        return jsonify({'status': 'erro', 'mensagem': 'Colaborador não encontrado'}), 404

    # Salva/Atualiza a avaliação atual
    avaliacao = Avaliacao.query.filter_by(colaborador_id=colaborador.id).first()
    if not avaliacao:
        avaliacao = Avaliacao(colaborador_id=colaborador.id)
        db.session.add(avaliacao)
    avaliacao.atributos = notas_numericas # Salva as notas já convertidas

    # Calcula o overall e salva no histórico
    overall_calculado = calcular_overall_com_notas(notas_numericas, processo_colaborador) # Usa as notas convertidas
    novo_historico = Historico(
        colaborador_id=colaborador.id,
        overall=overall_calculado,
        sub_atributos=notas_numericas # Salva também as notas convertidas
    )
    db.session.add(novo_historico)
    
    db.session.commit()
    return jsonify({'status': 'sucesso', 'mensagem': f'Avaliação de {nome_colaborador} salva!'})

@app.route('/api/colaborador/<int:colaborador_id>/historico')
@login_required
def get_historico_colaborador(colaborador_id):
    historico_db = Historico.query.filter_by(colaborador_id=colaborador_id).order_by(Historico.data.asc()).all()
    historico_list = [
        {"data": h.data.strftime('%Y-%m-%d'), "overall": h.overall}
        for h in historico_db
    ]
    return jsonify(historico_list)

@app.route('/api/colaborador/<int:colaborador_id>/salvar_insignias', methods=['POST'])
@login_required
def salvar_insignias_api(colaborador_id):
    colaborador = Colaborador.query.get_or_404(colaborador_id)
    ids_insignias = request.json.get('insignias', [])

    # Apaga as insígnias antigas
    Insignia.query.filter_by(colaborador_id=colaborador.id).delete()

    # Adiciona as novas
    for insignia_id in ids_insignias:
        nova_insignia = Insignia(colaborador_id=colaborador.id, insignia_id=insignia_id)
        db.session.add(nova_insignia)
    
    db.session.commit()
    return jsonify({'status': 'sucesso', 'mensagem': 'Insígnias salvas com sucesso!'})


# --- COMANDOS CLI PARA GERENCIAR O APP ---
@app.cli.command("init-db")
def init_db_command():
    """Cria as tabelas do banco de dados."""
    db.create_all()
    print("Banco de dados inicializado.")

@app.cli.command("seed")
def seed_database():
    """Popula a base de dados a partir dos ficheiros Excel e JSON iniciais."""
    print("Iniciando a migração de dados para o banco de dados...")

    # Migrar Utilizadores
    try:
        if os.path.exists('users.json'):
            with open('users.json', 'r', encoding='utf-8') as f:
                users_data = json.load(f)
            
            for user_id, user_info in users_data.items():
                existing_user = User.query.filter_by(email=user_info['email']).first()
                if not existing_user:
                    new_user = User(
                        nome=user_info['nome'], email=user_info['email'], cargo=user_info.get('cargo'),
                        password=user_info['password'], force_password_reset=user_info.get('force_password_reset', False)
                    )
                    db.session.add(new_user)
            db.session.commit()
            print(f"{len(users_data)} utilizadores verificados/adicionados.")
    except Exception as e:
        print(f"Erro ao migrar utilizadores: {e}")
        db.session.rollback()

    # Migrar Colaboradores
    try:
        if os.path.exists('Colaboradores.xlsx'):
            df = pd.read_excel('Colaboradores.xlsx')
            df = df.where(pd.notnull(df), None)

            for index, row in df.iterrows():
                if not row.get('Nome_completo'): continue
                
                existing_colab = Colaborador.query.filter_by(nome_completo=row['Nome_completo']).first()
                if not existing_colab:
                    turno_str = str(row.get('Turno', ''))
                    try:
                        turno_num = int(turno_str.split('º')[0]) if 'º' in turno_str else None
                    except (ValueError, IndexError):
                        turno_num = None

                    new_colab = Colaborador(
                        nome_completo=row['Nome_completo'], cargo=row.get('Cargo'), processo=row.get('Processo'),
                        turno=turno_str, turno_num=turno_num, nome_gestor_imediato=row.get('Nome_Gestor_Imediato'),
                        foto_url=row.get('Foto_URL')
                    )
                    db.session.add(new_colab)
            db.session.commit()
            print(f"{len(df)} registos de colaboradores verificados/adicionados.")
    except Exception as e:
        print(f"Erro ao migrar colaboradores: {e}")
        db.session.rollback()

    print("Migração de dados concluída!")

@app.route('/comparador')
@login_required
def comparador():
    colaboradores = get_dados_completos()
    # Apenas para a seleção inicial, não precisamos do overall aqui.
    colaboradores_ordenados = sorted(colaboradores, key=lambda x: x['Nome_completo'])
    return render_template('comparador.html', colaboradores=colaboradores_ordenados)

@app.route('/matriz_talentos/<nome_setor>/<int:num_turno>')
@login_required
def matriz_talentos(nome_setor, num_turno):
    colaboradores = get_dados_completos()
    for c in colaboradores:
        c['overall'] = calcular_overall_individual(c, PESOS)

    equipe_filtrada = [
        c for c in colaboradores 
        if c.get('Processo') == nome_setor 
        and c.get('Turno_Num') == num_turno
        and c.get('Cargo') in ['Operacional', 'Op Empilhadeira']
    ]
    matriz = [[[], [], []], [[], [], []], [[], [], []]]
    titulos_matriz = [["Enigma", "Forte Desempenho", "Alto Potencial"], ["Questionável", "Mantenedor", "Forte Desempenho"], ["Inadequado", "Questionável", "Risco"]]
    
    def get_posicao(score):
        if score >= 80: return 2
        if score >= 60: return 1
        return 0

    for c in equipe_filtrada:
        atributos = {item['nome_principal']: item['valor_principal'] for item in c['atributos_detalhados']}
        score_tecnica = atributos.get('Tecnica', 0)
        score_comportamento = atributos.get('Comportamento', 0)
        pos_x, pos_y = get_posicao(score_comportamento), get_posicao(score_tecnica)
        matriz[2 - pos_y][pos_x].append(c)
        
    return render_template('matriz_talentos.html', matriz=matriz, titulos=titulos_matriz, nome_setor=nome_setor, num_turno=num_turno)

@app.route('/grupo/<nome_grupo>')
@login_required
def grid_grupo(nome_grupo):
    # Verificação de segurança para garantir que apenas gestores acedem
    if current_user.cargo not in ["Coordenador - Log", "Gerente"]:
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for('home'))

    colaboradores = get_dados_completos()
    equipe_filtrada = []
    
    if nome_grupo == "Administrativos":
        cargos = ["Coordenador - Log", "Analista Log I", "Analista Log II", "Assistente Administrativo", "Especialista"]
        equipe_filtrada = [c for c in colaboradores if c.get('Cargo') in cargos]
    elif nome_grupo == "Técnicos":
        cargos = ["Técnico III - Log", "Assistente"]
        equipe_filtrada = [c for c in colaboradores if c.get('Cargo') in cargos]
    
    return render_template('grupo_grid.html', equipe=equipe_filtrada, nome_grupo=nome_grupo)

@app.route('/api/comparar', methods=['POST'])
@login_required
def api_comparar():
    try:
        ids_selecionados = request.json.get('ids', [])
        if not 2 <= len(ids_selecionados) <= 4:
            return jsonify({"erro": "Selecione de 2 a 4 colaboradores."}), 400
        
        ids_selecionados_int = [int(id_str) for id_str in ids_selecionados]
        
        colaboradores_todos = get_dados_completos()
        colaboradores_selecionados = [c for c in colaboradores_todos if c['id'] in ids_selecionados_int]

        # Calcula o overall para os selecionados
        for c in colaboradores_selecionados:
            c['overall'] = calcular_overall_individual(c, PESOS)

        # Prepara os dados para o gráfico
        dados_grafico = {'labels': list(ESTRUTURA_ATRIBUTOS.keys()), 'datasets': []}
        cores = ['#007bff', '#28a745', '#ffc107', '#dc3545']
        for i, c in enumerate(colaboradores_selecionados):
            dataset = {
                'label': c['Nome_completo'].split(' ')[0],
                'data': [item['valor_principal'] for item in c['atributos_detalhados']],
                'backgroundColor': cores[i % len(cores)]
            }
            dados_grafico['datasets'].append(dataset)
            
        return jsonify({'cards_data': colaboradores_selecionados, 'chart_data': dados_grafico})
        
    except Exception as e:
        print(f"ERRO na API /api/comparar: {e}")
        traceback.print_exc()
        return jsonify({"erro": "Ocorreu um erro interno no servidor."}), 500
    

# --- INICIALIZAÇÃO DO SERVIDOR ---
# --- INICIALIZAÇÃO DO SERVIDOR ---
if __name__ == '__main__':
    with app.app_context():
        # Cria as tabelas se elas não existirem
        db.create_all()
    # A linha app.run() é removida ou comentada para produção
    # app.run(debug=True)
