import sys, os
sys.path.append('../uc-rag')
from stub_rag import query, get_collection

q = "Who approves leave without pay?"
res = query(q)
print(f"Refused: {res['refused']}")
print(f"Answer: {res['answer']}")

collection = get_collection()
results = collection.query(query_embeddings=[[0]*384], n_results=10) # dummy query to see all
print("\nFirst 2 chunks in DB:")
for i in range(min(2, len(results['documents'][0]))):
    print(f"ID: {results['ids'][0][i]}")
    print(f"Doc: {results['documents'][0][i][:200]}...")
