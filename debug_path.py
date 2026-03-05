import tempfile
import platform

temp_dir = tempfile.mkdtemp()
base_path = str(temp_dir)
name = 'file.'
invalid_path = f'{base_path}/{name}'
print(f'base_path: {base_path}')
print(f'name: {name}')
print(f'invalid_path: {invalid_path}')

# Same logic as in validation function
path_parts = invalid_path.replace('\\', '/').split('/')
print(f'path_parts: {path_parts}')

for i, part in enumerate(path_parts):
    print(f'  part[{i}]: "{part}"')
    if part and part not in ('.', '..') and (part.endswith('.') or part.endswith(' ')):
        print(f'    -> Found problematic part: "{part}"')
        print('    -> Should raise ValueError')
    else:
        print(f'    -> OK')
