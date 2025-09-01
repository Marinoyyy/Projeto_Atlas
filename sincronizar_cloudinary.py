# sincronizar_cloudinary.py
import pandas as pd
import os
from unidecode import unidecode
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv

# Carrega as suas credenciais do Cloudinary do arquivo .env
load_dotenv()

# --- CONFIGURAÇÕES ---
ARQUIVO_COLABORADORES = 'Colaboradores.xlsx'
# A pasta onde estão as suas fotos originais para corrigir
PASTA_FOTOS_ORIGINAIS = 'fotos_para_corrigir'

def sincronizar_e_corrigir_fotos_cloudinary():
    """
    Faz o upload de fotos locais para o Cloudinary com um public_id padronizado
    e atualiza a planilha Excel com as URLs corretas e permanentes.
    """
    print("--- INICIANDO SCRIPT DE SINCRONIZAÇÃO COM CLOUDINARY (VERSÃO CORRIGIDA) ---")

    # 1. Configuração do Cloudinary
    try:
        cloudinary.config(
            cloud_name=os.getenv('CLOUD_NAME'),
            api_key=os.getenv('API_KEY'),
            api_secret=os.getenv('API_SECRET')
        )
        print("Credenciais do Cloudinary carregadas com sucesso.")
    except Exception as e:
        print(f"[ERRO FATAL] Falha ao configurar o Cloudinary. Verifique o seu ficheiro .env. Erro: {e}")
        return

    # 2. Ler a planilha de colaboradores
    try:
        df = pd.read_excel(ARQUIVO_COLABORADORES)
        # Garante que a coluna 'Nome_completo' é do tipo string
        df['Nome_completo'] = df['Nome_completo'].astype(str)
        print(f"Planilha '{ARQUIVO_COLABORADORES}' lida com sucesso.")
    except FileNotFoundError:
        print(f"[ERRO FATAL] A planilha '{ARQUIVO_COLABORADORES}' não foi encontrada.")
        return

    # 3. Encontrar e mapear as fotos locais de forma mais inteligente
    fotos_encontradas = {}
    print(f"Procurando fotos na pasta '{PASTA_FOTOS_ORIGINAIS}'...")
    for nome_arquivo in os.listdir(PASTA_FOTOS_ORIGINAIS):
        caminho_completo = os.path.join(PASTA_FOTOS_ORIGINAIS, nome_arquivo)
        if os.path.isfile(caminho_completo):
            # Limpa o nome do arquivo para ter uma chave de busca (ex: "maria-silva")
            # Remove sufixos como '_geeos6' e a extensão '.jpg'
            chave = unidecode(os.path.splitext(nome_arquivo)[0].split('_')[0].replace('-', ' ').lower())
            fotos_encontradas[chave] = caminho_completo

    print(f"{len(fotos_encontradas)} fotos encontradas e mapeadas.")

    # 4. Iterar sobre a planilha, fazer upload e atualizar URLs
    uploads_sucesso = 0
    erros_upload = 0
    for index, row in df.iterrows():
        nome_completo = row.get('Nome_completo')
        if pd.isna(nome_completo) or nome_completo.strip() == '':
            continue

        nome_normalizado = unidecode(nome_completo.lower().replace(' ', '-'))
        # Tenta encontrar a foto usando o nome normalizado como chave
        caminho_foto = fotos_encontradas.get(nome_normalizado)

        if caminho_foto:
            try:
                # O public_id será padronizado (ex: "maria-da-silva") para garantir um link permanente
                public_id_padrao = nome_normalizado

                print(f"  Fazendo upload para '{nome_completo}' com ID: '{public_id_padrao}'...")

                # Faz o upload, sobrescrevendo se já existir uma foto com esse ID
                upload_result = cloudinary.uploader.upload(
                    caminho_foto,
                    public_id=public_id_padrao,
                    overwrite=True,
                    unique_filename=False
                )

                # Pega a URL segura e final
                url_segura = upload_result.get('secure_url')

                # Atualiza a coluna 'Foto_URL' no DataFrame
                df.at[index, 'Foto_URL'] = url_segura
                print(f"  -> SUCESSO! URL: {url_segura}")
                uploads_sucesso += 1

            except Exception as e:
                print(f"  -> ERRO ao fazer upload para {nome_completo}: {e}")
                erros_upload += 1
        else:
            print(f"  [AVISO] Nenhuma foto local encontrada para: {nome_completo}")

    # 5. Salvar a planilha atualizada
    try:
        df.to_excel(ARQUIVO_COLABORADORES, index=False)
        print("\n--- SINCRONIZAÇÃO CONCLUÍDA ---")
        print(f"O arquivo '{ARQUIVO_COLABORADORES}' foi atualizado com sucesso.")
        print(f"Uploads realizados: {uploads_sucesso}")
        print(f"Falhas no upload: {erros_upload}")
    except Exception as e:
        print(f"\n[ERRO FATAL] Não foi possível salvar a planilha. Verifique se ela não está aberta. Erro: {e}")

# Executa a função principal
if __name__ == "__main__":
    sincronizar_e_corrigir_fotos_cloudinary()