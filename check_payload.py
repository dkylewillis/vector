from src.data_pipeline.vector_database import VectorDatabase

db = VectorDatabase('fayette')
results = db.client.scroll(collection_name='fayette', limit=1, with_payload=True)

if results[0]:
    payload = results[0][0].payload
    print('Sample payload:', payload)
    print('Available keys:', list(payload.keys()))
    
    # Check if there are nested keys
    for key, value in payload.items():
        print(f"{key}: {type(value)} = {value}")
else:
    print('No results found')
