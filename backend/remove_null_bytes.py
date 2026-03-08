# save as fix_null_bytes.py and run it
file_path = r"C:\Users\pc\ep-basic-school-fees\backend\apps\users\views.py"

# Read the file in binary mode
with open(file_path, 'rb') as f:
    content = f.read()

# Check for null bytes
if b'\x00' in content:
    print(f"Found {content.count(b'\\x00')} null bytes in the file!")
    
    # Remove null bytes
    clean_content = content.replace(b'\x00', b'')
    
    # Write back
    with open(file_path, 'wb') as f:
        f.write(clean_content)
    
    print("File cleaned successfully!")
else:
    print("No null bytes found")