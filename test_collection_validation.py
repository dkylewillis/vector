# Test collection name validation
def validate_collection_name(name):
    if not name or not name.strip():
        return False, 'Please enter a name for the new collection.'
    
    clean_name = name.strip().lower()
    if not clean_name.replace('_', '').replace('-', '').isalnum():
        return False, 'Collection name can only contain letters, numbers, hyphens, and underscores.'
    
    return True, clean_name

# Test various collection names
test_names = [
    '',
    '   ',
    'my-collection',
    'my_collection_123',
    'MyCollection',
    'collection with spaces',
    'collection@invalid',
    'valid123',
    'test-collection_v2'
]

print('Collection name validation tests:')
for name in test_names:
    valid, result = validate_collection_name(name)
    status = '✅' if valid else '❌'
    print(f'{status} "{name}" -> {result}')
