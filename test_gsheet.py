#!/usr/bin/env python
"""
Script de prueba para verificar la conexión OAuth2 con Google Sheets
"""
import os
import sys
import logging
from dotenv import load_dotenv

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(message)s')

# Cargar variables de entorno
load_dotenv()
SPREADSHEET_NAME = os.getenv('SPREADSHEET_NAME')

print(f"\n{'='*60}")
print(f"🧪 PRUEBA DE CONEXIÓN GOOGLE SHEETS")
print(f"{'='*60}")
print(f"\n📋 Sheet configurado: {SPREADSHEET_NAME}")

# Intentar conexión
try:
    print("\n🔗 Conectando con OAuth2...")
    import gspread
    
    # Primera vez abre navegador para autenticación
    gc = gspread.oauth()
    print("✅ Autenticación exitosa")
    
    print(f"\n📂 Abriendo spreadsheet: {SPREADSHEET_NAME}")
    spreadsheet = gc.open(SPREADSHEET_NAME)
    print("✅ Spreadsheet abierto")
    
    print("\n📄 Hojas disponibles:")
    for sheet in spreadsheet.worksheets():
        print(f"  - {sheet.title}")
    
    print("\n📝 Intentando acceder a la hoja 'Bot'...")
    worksheet = spreadsheet.worksheet('Bot')
    print("✅ Hoja 'Bot' encontrada")
    
    # Obtener primeras celdas
    print("\n📊 Primeras datos de la hoja:")
    data = worksheet.get_values('A1:E5')
    for row in data[:5]:
        print(f"  {row}")
    
    print(f"\n{'='*60}")
    print("✅ TODO FUNCIONA CORRECTAMENTE")
    print(f"{'='*60}\n")
    
except Exception as e:
    print(f"\n❌ ERROR: {str(e)}")
    print(f"\n{'='*60}")
    print("Soluciones:")
    print("1. Asegúrate de haber completado la autenticación OAuth")
    print("2. Verifica que el nombre del sheet sea correcto")
    print("3. Verifica que exista una hoja llamada 'Bot'")
    print(f"{'='*60}\n")
    sys.exit(1)
