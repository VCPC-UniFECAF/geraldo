"""Trava por processo para os comandos que mexem em saldo ou na fila.

O backend de demonstração é um processo só (SQLite): um Lock basta para impedir a perda de atualização
(duas reservas lendo o mesmo saldo) e duas entregas para o mesmo robô. Com vários workers, troque por
UPDATE condicional no banco ou por um banco com trava de linha.
"""
import functools
import threading

stock_lock = threading.RLock()


def serialized(execute):
    """Decorador do execute() de um comando: roda dentro de self._lock (injetado pelo construtor)."""

    @functools.wraps(execute)
    def wrapper(self):
        with self._lock:
            return execute(self)

    return wrapper
