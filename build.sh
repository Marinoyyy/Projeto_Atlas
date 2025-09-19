set -o errexit

pip install -r requirements.txt


flask db migrate -m "Adiciona coluna observacoes em Avaliacao"

flask db upgrade

#flask seed




