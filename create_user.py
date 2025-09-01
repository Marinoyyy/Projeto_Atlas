import pandas as pd
from werkzeug.security import generate_password_hash
# Importações necessárias da sua aplicação Flask
from app import app, db, User 

# Ficheiro Excel que serve como fonte de dados dos colaboradores
ARQUIVO_COLABORADORES = 'Colaboradores.xlsx'

def criar_utilizador():
    """
    Ferramenta de linha de comando para criar um novo utilizador no banco de dados.
    """
    print("--- Ferramenta de Criação de Utilizadores (Versão Base de Dados) ---")
    
    try:
        df_colaboradores = pd.read_excel(ARQUIVO_COLABORADORES)
        # Garante que a coluna de e-mail está em minúsculas para comparação
        df_colaboradores['E-mail'] = df_colaboradores['E-mail'].str.lower()
    except FileNotFoundError:
        print(f"[ERRO] O ficheiro '{ARQUIVO_COLABORADORES}' não foi encontrado. Abortando.")
        return

    email = input("Digite o email do novo utilizador: ").lower()

    # Procura as informações do colaborador no ficheiro Excel
    colaborador_info_list = df_colaboradores[df_colaboradores['E-mail'] == email].to_dict('records')
    if not colaborador_info_list:
        print(f"[ERRO] Email '{email}' não encontrado na planilha de colaboradores.")
        return
        
    colaborador_info = colaborador_info_list[0]
    nome_colaborador = colaborador_info.get('Nome_completo')
    cargo_colaborador = colaborador_info.get('Cargo')

    # --- Lógica de Banco de Dados ---
    # O 'with app.app_context()' é crucial para que o script tenha acesso à base de dados
    with app.app_context():
        # Verifica se o utilizador já existe no banco de dados
        utilizador_existente = User.query.filter_by(email=email).first()
        if utilizador_existente:
            print(f"[ERRO] O email '{email}' já está registado no sistema.")
            return
            
        temp_password = input(f"Digite a SENHA TEMPORÁRIA para {nome_colaborador}: ")
        if not temp_password:
            print("[ERRO] A senha não pode estar em branco.")
            return

        # Cria o hash da senha
        password_hash = generate_password_hash(temp_password, method='pbkdf2:sha256')
        
        # Cria a nova instância do utilizador com o modelo User
        novo_utilizador = User(
            nome=nome_colaborador,
            email=email,
            cargo=cargo_colaborador,
            password=password_hash,
            force_password_reset=True  # Força a redefinição de senha no primeiro login
        )
        
        # Adiciona o novo utilizador à sessão e salva no banco de dados
        db.session.add(novo_utilizador)
        db.session.commit()
    
    print("\n-------------------------------------------------")
    print(f"✅ Utilizador '{nome_colaborador}' criado com sucesso no banco de dados!")
    print(f"   - Email: {email}")
    print(f"   - Senha Temporária: {temp_password}")
    print("   - O utilizador terá de redefinir a senha no primeiro login.")
    print("-------------------------------------------------")


if __name__ == '__main__':
    criar_utilizador()