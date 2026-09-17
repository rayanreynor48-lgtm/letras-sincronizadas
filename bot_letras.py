import requests
import re
import time
from pathlib import Path

# Intentar importar pygame para audio
try:
    import pygame
    AUDIO_DISPONIBLE = True
except ImportError:
    AUDIO_DISPONIBLE = False
    print("[AVISO] pygame no instalado. Ejecuta: pip install pygame")

# CONFIGURACION
BASE_URL = "http://127.0.0.1:5000"
CARPETA_SRT_DESCARGA = Path(__file__).parent / "srt_descargados"
CARPETA_SRT_DESCARGA.mkdir(exist_ok=True)

# COLORES PARA LA CONSOLA
class Colores:
    VERDE = "\033[92m"
    CIAN = "\033[96m"
    AMARILLO = "\033[93m"
    MAGENTA = "\033[95m"
    BLANCO = "\033[97m"
    RESET = "\033[0m"

def normalizar(texto):
    if not texto: return ""
    t = texto.lower().strip()
    t = re.sub(r'[_\\/\\-]+', ' ', t)
    t = re.sub(r'\s+', ' ', t)
    t = re.sub(r'[^\w\s]', '', t)
    return t

def buscar_por_nombre(nombre_archivo):
    print("\n[BUSCANDO] Para:", nombre_archivo)
    consulta = normalizar(nombre_archivo)
    
    try:
        resp = requests.get(
            f"{BASE_URL}/api/buscar?q={requests.utils.quote(consulta)}"
        )
        resp.raise_for_status()
        datos = resp.json()
    except Exception as e:
        print("[ERROR] No se pudo conectar al servidor:", e)
        return None

    if datos["encontrados"] == 0:
        print("[INFO] No se encontro letra para esta cancion")
        return None

    print(f"[INFO] Encontrados {datos['encontrados']} resultados:")
    for i, c in enumerate(datos["resultados"], 1):
        print(f"  {i}. {c['artista_original']} - {c['cancion_original']}")

    if len(datos["resultados"]) == 1:
        return datos["resultados"][0]
    
    while True:
        opcion = input("\nElije el numero correcto (o presiona Enter para el primero): ").strip()
        if not opcion:
            return datos["resultados"][0]
        if opcion.isdigit() and 1 <= int(opcion) <= len(datos["resultados"]):
            return datos["resultados"][int(opcion) - 1]
        print("[AVISO] Opcion no valida")

def descargar_srt(cancion):
    ruta_web = cancion["ruta"]
    nombre = cancion["archivo"]
    guardado = CARPETA_SRT_DESCARGA / nombre

    print("[DESCARGANDO]", nombre)
    resp = requests.get(f"{BASE_URL}{ruta_web}")
    resp.raise_for_status()
    
    with open(guardado, "wb") as f:
        f.write(resp.content)
    
    print("[GUARDADO EN]", guardado)
    return str(guardado)

def leer_srt(ruta_srt):
    lineas = []
    with open(ruta_srt, "r", encoding="utf-8") as f:
        contenido = f.read().strip()

    bloques = re.split(r'\n\s*\n', contenido)
    for bloque in bloques:
        partes = bloque.splitlines()
        if len(partes) >= 3:
            m = re.match(
                r'(\d+):(\d+):(\d+)[,.](\d+)\s*-->\s*(\d+):(\d+):(\d+)[,.](\d+)',
                partes[1]
            )
            if m:
                h1, mi1, s1, ms1, h2, mi2, s2, ms2 = map(int, m.groups())
                inicio = h1 * 3600 + mi1 * 60 + s1 + ms1 / 1000
                fin = h2 * 3600 + mi2 * 60 + s2 + ms2 / 1000
                lineas.append({
                    "inicio": inicio,
                    "fin": fin,
                    "texto": "\n".join(partes[2:])
                })
    return sorted(lineas, key=lambda x: x["inicio"])

def reproducir_con_audio(ruta_mp3, ruta_srt):
    letras = leer_srt(ruta_srt)
    if not letras:
        print("[ERROR] No se pudieron leer las letras")
        return

    print("\n" + "="*60)
    print("LETRAS SINCRONIZADAS")
    print("="*60)
    print("Archivo MP3:", ruta_mp3)
    print("Archivo SRT:", Path(ruta_srt).name)
    print()

    if AUDIO_DISPONIBLE:
        pygame.mixer.init()
        try:
            pygame.mixer.music.load(ruta_mp3)
            print("[INICIANDO] En 3 segundos...")
            time.sleep(3)
            pygame.mixer.music.play()
        except Exception as e:
            print("[ERROR] No se pudo reproducir el audio:", e)
            return
    else:
        print("[AVISO] Reproduce el archivo MP3 manualmente ahora")
        input("Presiona Enter cuando empiece la cancion...")

    tiempo_inicio = time.time()
    indice = 0
    ultima = ""
    # Colores alternos para que se vean bonitas
    lista_colores = [Colores.VERDE, Colores.CIAN, Colores.AMARILLO, Colores.MAGENTA]
    color_actual = 0

    print("\n--- LETRAS ---")
    try:
        while True:
            if AUDIO_DISPONIBLE and not pygame.mixer.music.get_busy():
                print("\n[FIN] Cancion terminada")
                break

            actual = time.time() - tiempo_inicio

            while indice < len(letras) and actual >= letras[indice]["fin"]:
                indice += 1

            if indice < len(letras) and actual >= letras[indice]["inicio"]:
                texto = letras[indice]["texto"]
                if texto != ultima:
                    # Mostrar solo el texto con color, SIN TIEMPO
                    print(f"{lista_colores[color_actual]}{texto}{Colores.RESET}")
                    color_actual = (color_actual + 1) % len(lista_colores)
                    ultima = texto

            if indice >= len(letras):
                print("\n[FIN] Letras completadas")
                if AUDIO_DISPONIBLE:
                    pygame.mixer.music.stop()
                break

            time.sleep(0.05)

    except KeyboardInterrupt:
        print("\n[DETENIDO] Por el usuario")
        if AUDIO_DISPONIBLE:
            pygame.mixer.music.stop()
            pygame.mixer.quit()

    if AUDIO_DISPONIBLE:
        pygame.mixer.quit()

def menu_principal():
    print("="*60)
    print("BUSCADOR DE LETRAS")
    print("="*60)
    print("Servidor:", BASE_URL)
    print("Audio disponible:", "SI" if AUDIO_DISPONIBLE else "NO")
    print("Carpeta de descargas:", CARPETA_SRT_DESCARGA)
    print()

    while True:
        print("-"*60)
        ruta_mp3 = input(
            "Escribe la ruta completa del archivo .mp3\n"
            "Ejemplo: F:\\motog09\\nombre de la carpeta\\cancion.mp3\n"
            "O escribe 'salir' para terminar:\n"
            ">>> "
        ).strip()

        if ruta_mp3.lower() in ["salir", "q", "exit"]:
            print("Hasta luego!")
            break

        if not ruta_mp3:
            continue

        archivo = Path(ruta_mp3)
        if not archivo.exists():
            print("[ERROR] No existe el archivo:", ruta_mp3)
            continue
        if archivo.suffix.lower() != ".mp3":
            print("[AVISO] No es un archivo .mp3:", archivo.name)
            continue

        print("[OK] Archivo valido:", archivo.name)

        cancion = buscar_por_nombre(archivo.stem)
        if not cancion:
            continue

        ruta_srt = descargar_srt(cancion)

        reproducir = input("\nReproducir con letras sincronizadas? (s/n): ").strip().lower()
        if reproducir in ["s", "si", "sí"]:
            reproducir_con_audio(ruta_mp3, ruta_srt)

        print()

if __name__ == "__main__":
    menu_principal()