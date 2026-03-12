import os
import sys
import pprint

print("="*50)
print("🔍 DIAGNÓSTICO DO SISTEMA")
print("="*50)

print(f"\n📌 Python version: {sys.version}")
print(f"📌 Current directory: {os.getcwd()}")
print(f"📌 Files in current dir: {os.listdir('.')}")

print("\n📌 Environment variables:")
for key in ['RENDER', 'DATABASE_URL', 'SECRET_KEY']:
    print(f"   {key}: {os.getenv(key, '❌ Não definido')}")

print("\n📌 Checking write permissions:")
test_file = '/tmp/test_write.txt'
try:
    with open(test_file, 'w') as f:
        f.write('test')
    print(f"   ✅ /tmp is writable")
    os.remove(test_file)
except Exception as e:
    print(f"   ❌ /tmp is NOT writable: {e}")

test_local = './test_write.txt'
try:
    with open(test_local, 'w') as f:
        f.write('test')
    print(f"   ✅ Current dir is writable")
    os.remove(test_local)
except Exception as e:
    print(f"   ❌ Current dir is NOT writable: {e}")

print("="*50)
