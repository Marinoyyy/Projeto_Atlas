#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

flask db init
flask db migrate -m "Initial migration."
flask db upgrade

# O comando abaixo irá popular o seu banco de dados com os dados iniciais
# Remova ou comente esta linha após o primeiro deploy bem-sucedido
#flask seed