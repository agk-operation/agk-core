#!/bin/sh
set -e

host="$1"
shift
cmd="$@"

echo "⏳ Aguardando o banco de dados em $host..."
until pg_isready -h "$host" -p 5432 -U postgres > /dev/null 2>&1; do
  sleep 2
done

echo "✅ Banco de dados disponível! Executando comando..."
exec $cmd
