# cd C:\Users\Robot\Documents\markiv\;.venv\Scripts\python.exe update_chromedriver.py 139.0.7258.68 # noqa
# cd C:\Users\Robot\Documents\markiv\;.venv\Scripts\python.exe update_chromedriver.py 140.0.7339.82 # noqa
# cd C:\Users\Robot\Documents\markiv\;.venv\Scripts\Activate.ps1;python;update_chromedriver.py 141.0.7390.54 # noqa
# cd C:\Users\Robot\Documents\markiv\;.venv\Scripts\Activate.ps1;python;update_chromedriver.py 142.0.7444.61
# C:\Users\Robot\Documents\markiv\.venv\Scripts\Activate.bat;python C:\Users\Robot\Documents\markiv\update_chromedriver.py 143.0.7499.42
# -*- coding: utf-8 -*-
import os
import sys
import requests
import zipfile
import json
import subprocess
import shutil
import re
import platform


def get_installed_chrome_version():
    """
    Detecta la versión de Google Chrome instalada en el sistema Windows.
    Busca en las rutas estándar para versiones de 64 y 32 bits.
    """
    # Rutas estándar de instalación de Chrome
    chrome_paths = [
        os.path.join(
            os.environ.get("ProgramFiles", "C:\\Program Files"),
            "Google",
            "Chrome",
            "Application",
            "chrome.exe",
        ),
        os.path.join(
            os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"),
            "Google",
            "Chrome",
            "Application",
            "chrome.exe",
        ),
    ]

    for path in chrome_paths:
        if os.path.exists(path):
            try:
                # Ejecuta chrome.exe --version y captura la salida
                # La salida es similar a: "Google Chrome 123.0.6312.122"
                print(f"Intentando detectar la versión de Chrome en: {path}")
                result = subprocess.run(
                    [path, "--version"],
                    capture_output=True,
                    text=True,
                    check=True,
                    encoding="utf-8",
                )
                version_match = re.search(r"(\d+\.\d+\.\d+\.\d+)", result.stdout) # noqa
                if version_match:
                    version = version_match.group(1)
                    print(f"Versión de Google Chrome detectada: {version}")
                    return version
            except (subprocess.CalledProcessError, FileNotFoundError) as e:
                print(
                    f"Error al ejecutar Chrome en {path}: {e}", file=sys.stderr
                )
                # Continúa intentando con la siguiente ruta si falla
                continue
    return None


def get_chromedriver_download_url(chrome_version: str):
    """
    Determina la URL de descarga de chromedriver compatible con la
    versión de Chrome dada. Maneja la nueva API (>= 115) y la antigua (< 115).
    """
    try:
        major_version = int(chrome_version.split(".")[0])
    except ValueError as e:
        raise ValueError(
            f"Formato de versión de Chrome inválido: {chrome_version}. "
            f"Detalle: {e}"
        )

    if major_version >= 115:
        print(
            f"Chrome versión {major_version} (>= 115): Usando el nuevo método de descarga." # noqa
        )
        json_url = (
            "https://googlechromelabs.github.io/chrome-for-testing/"
            "last-known-good-versions-with-downloads.json"
        )

        try:
            response = requests.get(json_url, timeout=10)
            response.raise_for_status()  # Lanza un error HTTP si la respuesta no es 200 OK # noqa
            data = response.json()

            stable_channel = data.get("channels", {}).get("Stable")
            if not stable_channel:
                raise Exception(
                    "No se encontró el canal 'Stable' en el JSON de "
                    "Chrome for Testing."
                )

            chromedriver_downloads = stable_channel.get("downloads", {}).get(
                "chromedriver", []
            )

            # Priorizar win64, luego win32. Se asume que el sistema es Windows.
            platform_arch = "win64" if platform.machine().endswith("64") else "win32" # noqa
            # *** CORRECCIÓN: Definir la arquitectura alterna aquí ***
            alternate_platform_arch = "win32" if platform_arch == "win64" else "win64" # noqa

            chromedriver_url = None
            found_platform = None

            # Buscar la arquitectura principal
            for entry in chromedriver_downloads:
                if entry.get("platform") == platform_arch:
                    chromedriver_url = entry.get("url")
                    found_platform = platform_arch
                    break

            # Si no se encontró, buscar la arquitectura alternativa
            if not chromedriver_url:
                for entry in chromedriver_downloads:
                    if entry.get("platform") == alternate_platform_arch:
                        chromedriver_url = entry.get("url")
                        found_platform = alternate_platform_arch
                        break

            if chromedriver_url:
                print(
                    f"URL de ChromeDriver ({found_platform}) para Chrome "
                    f"{chrome_version}: {chromedriver_url}"
                )
                return chromedriver_url
            else:
                raise Exception(
                    f"No se encontró un enlace de descarga de ChromeDriver compatible " # noqa
                    f"({platform_arch} o {alternate_platform_arch}) "
                    f"para la versión estable de Chrome."
                )

        except requests.exceptions.RequestException as e:
            raise Exception(f"Error al obtener el JSON de Chrome for Testing: {e}") # noqa
        except json.JSONDecodeError as e:
            raise Exception(f"Error al decodificar el JSON de Chrome for Testing: {e}") # noqa
        except Exception as e:
            raise Exception(f"Error al procesar los datos de Chrome for Testing: {e}") # noqa

    else:
        print(
            f"Chrome versión {major_version} (< 115): Usando el método de descarga antiguo." # noqa
        )
        latest_release_url = (
            f"https://chromedriver.storage.googleapis.com/"
            f"LATEST_RELEASE_{major_version}"
        )
        try:
            response = requests.get(latest_release_url, timeout=10)
            response.raise_for_status()
            chromedriver_version = response.text.strip()
            print(f"Versión de ChromeDriver compatible: {chromedriver_version}") # noqa

            download_url = (
                f"https://chromedriver.storage.googleapis.com/"
                f"{chromedriver_version}/chromedriver_win32.zip"
            )
            print(f"URL de descarga de ChromeDriver: {download_url}")
            return download_url
        except requests.exceptions.RequestException as e:
            raise Exception(
                f"Error al obtener la URL de ChromeDriver para versiones < 115: {e}" # noqa
            )


def download_and_extract_chromedriver(download_url: str, temp_dir: str):
    """
    Descarga el archivo ZIP de chromedriver y extrae chromedriver.exe.
    Retorna la ruta completa al archivo chromedriver.exe extraído.
    """
    zip_file_path = os.path.join(temp_dir, "chromedriver.zip")

    print(f"Descargando ChromeDriver desde: {download_url}")
    try:
        with requests.get(download_url, stream=True, timeout=30) as r:
            r.raise_for_status()
            with open(zip_file_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        print("Descarga completa.")
    except requests.exceptions.RequestException as e:
        raise Exception(f"Error al descargar ChromeDriver: {e}")

    print("Extrayendo chromedriver.exe...")
    extracted_path = os.path.join(temp_dir, "extracted")
    os.makedirs(extracted_path, exist_ok=True)

    chromedriver_exe_name = "chromedriver.exe"
    extracted_chromedriver_path = None

    try:
        with zipfile.ZipFile(zip_file_path, "r") as zip_ref:
            found = False
            # Recorrer los miembros del ZIP para encontrar chromedriver.exe.
            # En la nueva API, puede estar dentro de una subcarpeta (ej: chromedriver-win64/). # noqa
            for member in zip_ref.namelist():
                if member.endswith(chromedriver_exe_name):
                    # Extraer solo el chromedriver.exe
                    zip_ref.extract(member, extracted_path)
                    # La ruta final será dentro de la carpeta extraída,
                    # manteniendo la estructura del ZIP si existe.
                    extracted_chromedriver_path = os.path.join(
                        extracted_path, member
                    )
                    found = True
                    break
            if not found:
                raise Exception(
                    "chromedriver.exe no se encontró dentro del archivo ZIP."
                )
        print("Extracción completa.")
        return extracted_chromedriver_path
    except zipfile.BadZipFile as e:
        raise Exception(f"El archivo descargado no es un ZIP válido: {e}")
    except Exception as e:
        raise Exception(f"Error al extraer el archivo ZIP: {e}")


def copy_to_chocolatey_bin(source_path: str):
    """
    Copia chromedriver.exe desde la ruta de origen a la carpeta 'bin' de Chocolatey. # noqa
    """
    chocolatey_bin_dir = r"C:\ProgramData\chocolatey\bin"
    destination_path = os.path.join(chocolatey_bin_dir, "chromedriver.exe")

    print(f"Copiando chromedriver.exe a {destination_path}...")

    if not os.path.exists(chocolatey_bin_dir):
        print(
            f"ADVERTENCIA: El directorio de Chocolatey bin '{chocolatey_bin_dir}' " # noqa
            "no existe. Intentando crearlo (requiere permisos de administrador)." # noqa
        )
        try:
            os.makedirs(chocolatey_bin_dir, exist_ok=True)
        except OSError as e:
            raise OSError(
                f"ERROR: No se pudo crear el directorio de Chocolatey bin. "
                f"Asegúrate de ejecutar el script como ADMINISTRADOR. Error: {e}" # noqa
            )

    try:
        shutil.copy(source_path, destination_path)
        print("¡chromedriver.exe actualizado y colocado en Chocolatey bin con éxito!") # noqa
    except PermissionError:
        raise PermissionError(
            f"ERROR: Permiso denegado. No se puede copiar a "
            f"'{destination_path}'. Asegúrate de ejecutar el script "
            "como ADMINISTRADOR."
        )
    except Exception as e:
        raise Exception(
            f"Error al copiar chromedriver.exe al directorio de Chocolatey: {e}" # noqa
        )


def get_user_version_choice():
    """
    Pregunta al usuario qué versión de ChromeDriver quiere descargar.
    Ofrece opciones: detectar automáticamente, especificar manualmente,
    o usar argumento de línea de comandos.
    """
    print("\n=== ACTUALIZACIÓN DE CHROMEDRIVER ===")
    print("¿Qué versión de ChromeDriver quieres descargar?")
    print("1. Detectar automáticamente la versión de Chrome instalada")
    print("2. Especificar manualmente la versión de Chrome")
    print("3. Usar versión proporcionada como argumento de línea de comandos")

    while True:
        try:
            choice = input("\nSelecciona una opción (1, 2 o 3): ").strip()

            if choice == "1":
                print("Detectando automáticamente la versión de Chrome...")
                detected_version = get_installed_chrome_version()
                if detected_version:
                    confirm = input(
                        f"¿Confirmas usar la versión detectada "
                        f"{detected_version}? (s/n): "
                    ).strip().lower()
                    if confirm in ['s', 'si', 'sí', 'y', 'yes']:
                        return detected_version
                    else:
                        continue
                else:
                    print(
                        "No se pudo detectar la versión de Chrome. "
                        "Intenta otra opción."
                    )
                    continue

            elif choice == "2":
                while True:
                    version = input(
                        "Ingresa la versión de Chrome "
                        "(ej: 123.0.6312.122): "
                    ).strip()
                    if version and re.match(r'^\d+\.\d+\.\d+\.\d+$', version):
                        return version
                    else:
                        print("Formato inválido. Usa el formato: 123.0.6312.122")

            elif choice == "3":
                if len(sys.argv) > 1:
                    version = sys.argv[1]
                    print(f"Usando versión del argumento: {version}")
                    return version
                else:
                    print("No se proporcionó ningún argumento de línea de comandos.")
                    continue

            else:
                print("Opción inválida. Por favor, selecciona 1, 2 o 3.")

        except KeyboardInterrupt:
            print("\n\nProceso cancelado por el usuario.")
            sys.exit(0)
        except Exception as e:
            print(f"Error: {e}")


def main():
    """
    Función principal para orquestar la actualización de chromedriver.
    """
    chrome_version_param = None
    if len(sys.argv) > 1:
        chrome_version_param = sys.argv[1]
        print(
            f"Versión de Chrome proporcionada como argumento: {chrome_version_param}" # noqa
        )
        # Preguntar al usuario si quiere usar esta versión o elegir otra opción
        chrome_version = get_user_version_choice()
    else:
        print(
            "No se proporcionó la versión de Chrome como argumento."
        )
        chrome_version = get_user_version_choice()

    # Directorio temporal para descargas y extracción
    # Ubicado en el directorio temporal del sistema.
    temp_dir = os.path.join(
        os.environ.get("TEMP", "C:\\Temp"), "ChromeDriverUpdate"
    )

    # Limpiar directorio temporal antes de empezar (por si hay restos de ejecuciones previas) # noqa
    if os.path.exists(temp_dir):
        print(f"Limpiando directorio temporal existente: {temp_dir}")
        try:
            shutil.rmtree(temp_dir)
            print("Directorio temporal limpiado.")
        except OSError as e:
            print(
                f"ADVERTENCIA: No se pudo limpiar completamente el directorio "
                f"temporal '{temp_dir}'. Por favor, elimínalo manualmente. Detalle: {e}", # noqa
                file=sys.stderr,
            )
            # Continuar de todos modos, la sobreescritura podría funcionar

    # Crear el directorio temporal para la ejecución actual
    os.makedirs(temp_dir, exist_ok=True)

    try:
        download_url = get_chromedriver_download_url(chrome_version)
        extracted_chromedriver_path = download_and_extract_chromedriver(
            download_url, temp_dir
        )
        copy_to_chocolatey_bin(extracted_chromedriver_path)

        print("\nProceso finalizado. El directorio temporal es:", temp_dir)
        print("Si el proceso fue exitoso, puedes eliminarlo.")

    except Exception as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        print(
            "Asegúrate de ejecutar el script como ADMINISTRADOR.", file=sys.stderr # noqa
        )
    finally:
        # Aquí se podría añadir una limpieza automática al final,
        # pero es útil dejarlo si hay un error para depuración.
        # Por ahora, se informa al usuario para que lo limpie manualmente.
        pass


if __name__ == "__main__":
    main()
