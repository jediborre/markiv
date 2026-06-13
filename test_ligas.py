from utils import gsheet

wks = gsheet('Ligas')
if wks:
    print(f"Hoja: {wks.title}")
    print(f"Métodos disponibles con 'all': {[m for m in dir(wks) if 'all' in m.lower()]}")
    
    # Prueba get_all_values()
    data = wks.get_all_values()
    print(f"\nPrimeras 3 filas:")
    for i, row in enumerate(data[:3]):
        print(f"  Fila {i}: {row}")
else:
    print("Error conectando a Google Sheets")
