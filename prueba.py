marcador = [
    ['0', 0, 0],
    ['1', 0, 0],
    ['72', 1, 0],
    ['73', 1, 1],
    ['74', 1, 1],
    ['74', 1, 1],
    ['74', 1, 1],
    ['75', 1, 1],
    ['76', 1, 1],
    ['78', 1, 1],
    ['80', 1, 1],
    ['81', 1, 1],
    ['81', 1, 1],
    ['82', 1, 1],
    ['84', 1, 1],
    ['84', 1, 1],
    ['86', 2, 1],
    ['86', 2, 1],
    ['86', 2, 1],
    ['88', 2, 1],
    ['89', 2, 1],
    ['89', 2, 1],
    ['90+', 2, 2],
    ['90+', 2, 2],
    ['90+', 2, 2]
]

goles_local_anterior = 0
goles_visitante_anterior = 0

print("Detectando nuevos goles:")
print("-" * 20)

# Recorremos cada registro en el marcador
for registro in marcador:
    minuto_actual = registro[0]
    goles_local_actual = registro[1]
    goles_visitante_actual = registro[2]

    # Comprobar si el equipo local anotó (comparado con el registro anterior)
    if goles_local_actual > goles_local_anterior:
        print(f"Minuto {minuto_actual}: GOL LOCAL")

    # Comprobar si el equipo visitante anotó (comparado con el registro anterior)
    if goles_visitante_actual > goles_visitante_anterior:
        print(f"Minuto {minuto_actual}: GOL VISITANTE")

    # Actualizamos los goles anteriores para la siguiente comparación
    goles_local_anterior = goles_local_actual
    goles_visitante_anterior = goles_visitante_actual

print("-" * 20)
print("Análisis completo.")
