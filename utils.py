def es_momio_americano(texto):
    try:
        momio = int(texto) # noqa
        return True
    except ValueError:
        return False
