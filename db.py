import os
import requests
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

def get_headers():
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }

class Table:
    def __init__(self, name):
        self.name  = name
        self.url   = f"{SUPABASE_URL}/rest/v1/{name}"
        self.query = ""
        self._data = None

    def select(self, cols="*"):
        self.query = f"?select={cols}"
        return self

    def insert(self, data):
        self._data = data
        return self

    def update(self, data):
        self._data = data
        return self

    def delete(self):
        self._data = None
        return self

    def eq(self, col, val):
        sep = "&" if "?" in self.query else "?"
        self.query += f"{sep}{col}=eq.{val}"
        return self

    def neq(self, col, val):
        sep = "&" if "?" in self.query else "?"
        self.query += f"{sep}{col}=neq.{val}"
        return self

    def order(self, col, desc=False):
        sep = "&" if "?" in self.query else "?"
        direction = "desc" if desc else "asc"
        self.query += f"{sep}order={col}.{direction}"
        return self

    def limit(self, n):
        sep = "&" if "?" in self.query else "?"
        self.query += f"{sep}limit={n}"
        return self

    def execute(self):
        url  = self.url + self.query
        hdrs = get_headers()

        try:
            if self._data is not None:
                # Détecter UPDATE vs INSERT
                is_update = (
                    self.query and
                    "=eq." in self.query and
                    not self.query.strip().startswith("?select")
                )
                if is_update:
                    r = requests.patch(url, json=self._data, headers=hdrs, timeout=15)
                else:
                    r = requests.post(self.url, json=self._data, headers=hdrs, timeout=15)
            elif self._data is None and hasattr(self, '_delete') and self._delete:
                r = requests.delete(url, headers=hdrs, timeout=15)
            else:
                r = requests.get(url, headers=hdrs, timeout=15)

            r.raise_for_status()

            try:
                data = r.json()
            except Exception:
                data = []

            if isinstance(data, dict) and "message" in data:
                raise Exception(data.get("message", "Erreur Supabase"))

        except requests.exceptions.ConnectionError as e:
            raise Exception(f"Connexion Supabase impossible : {e}")
        except requests.exceptions.Timeout:
            raise Exception("Timeout Supabase — réessayez.")
        except requests.exceptions.HTTPError as e:
            raise Exception(f"Erreur HTTP Supabase : {e}")

        class Result:
            pass

        result      = Result()
        result.data = data if isinstance(data, list) else [data] if data else []
        return result


class SupabaseClient:
    def table(self, name):
        return Table(name)

    def _delete_table(self, name):
        t = Table(name)
        t._delete = True
        return t


_client = None

def get_db() -> SupabaseClient:
    global _client
    if _client is None:
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise Exception("SUPABASE_URL et SUPABASE_KEY manquants dans .env")
        _client = SupabaseClient()
    return _client
    