"""
Configuration pytest : base SQLite temporaire + clés RSA courtes (tests rapides).
Les variables d'environnement doivent être posées AVANT l'import de l'application.
"""
import os
import tempfile

_tmpdir = tempfile.mkdtemp(prefix="cobalt-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{os.path.join(_tmpdir, 'test.db')}"
os.environ["RSA_KEY_BITS"] = "512"
