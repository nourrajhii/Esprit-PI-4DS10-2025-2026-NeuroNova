import sys, os
sys.path.insert(0, '/app')
os.chdir('/app')

from app.services.rag import ask_with_metrics
from app.services.vector_store import init_db, _tokenize

db = init_db()
print(f"DB: {type(db).__name__}, docs: {len(db.docs) if hasattr(db,'docs') else '?'}")
print()

# Test tokenizer on key terms
for term in ["hypothèque", "notaire", "locataire", "permis de construire", "acheteur"]:
    tokens = _tokenize(term)
    print(f"  tokenize({term!r}) = {tokens}")
print()

tests = [
    "quel est le role du notaire dans une transaction immobiliere",
    "comment fonctionne une hypotheque en Tunisie",
    "quels sont les droits du locataire en cas d expulsion",
    "comment obtenir un permis de construire",
    "quels documents pour acheter un bien immobilier",
]

for q in tests:
    r = ask_with_metrics(q, k=4)
    qt = r["question_type"]
    lang = r["lang"]
    metrics = r["metrics"]
    answer = r["answer"]
    print(f"Q: {q}")
    print(f"  TYPE={qt} LANG={lang} CHUNKS={len(metrics)}")
    for m in metrics[:3]:
        print(f"  [{m['source']}] combined={m['nlp_combined']} | {m['snippet'][:80]}")
    print(f"  ANSWER: {answer[:200]}")
    print()
