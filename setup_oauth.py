#!/usr/bin/env python
"""
Script para generar credenciales OAuth2 iniciales
Primera vez: abre navegador para autenticar
"""
import os
import sys
import webbrowser
from pathlib import Path

print("\n" + "="*60)
print("🔐 CONFIGURACIÓN INICIAL DE GOOGLE SHEETS")
print("="*60)

# Crear carpeta de credenciales
creds_dir = Path.home() / ".config" / "gspread"
creds_dir.mkdir(parents=True, exist_ok=True)

print(f"\n1. Vamos a autenticar con tu cuenta de Google...")
print(f"2. Se abrirá un navegador en unos segundos")
print(f"3. Selecciona tu cuenta y autoriza el acceso")

input("\n⏳ Presiona ENTER para continuar...")

try:
    print("\n🔗 Conectando...")
    import gspread
    
    # Esto abre el navegador automáticamente
    gc = gspread.oauth()
    
    print("\n✅ ¡AUTENTICACIÓN EXITOSA!")
    print(f"✅ Credenciales guardadas en: {creds_dir}")
    
    # Verificar que funciona
    print("\n📂 Accediendo a tus Google Sheets...")
    from dotenv import load_dotenv
    load_dotenv()
    
    SPREADSHEET_NAME = os.getenv('SPREADSHEET_NAME')
    if SPREADSHEET_NAME:
        spreadsheet = gc.open(SPREADSHEET_NAME)
        print(f"✅ Sheet '{SPREADSHEET_NAME}' encontrado")
        
        hojas = [s.title for s in spreadsheet.worksheets()]
        print(f"✅ Hojas disponibles: {', '.join(hojas)}")
        
        if 'Bot' in hojas:
            print(f"✅ La hoja 'Bot' existe")
    
    print("\n" + "="*60)
    print("✅ TODO LISTO - Ya puedes ejecutar tu programa")
    print("="*60 + "\n")
    
except Exception as e:
    print(f"\n❌ ERROR: {str(e)}")
    print(f"\nVerifica:")
    print("- Que aceptaras los permisos en el navegador")
    print("- Que tengas conexión a internet")
    print("- Que tu cuenta de Google tenga acceso al sheet")
    sys.exit(1)
