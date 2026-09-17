from flask import Flask, render_template, request, jsonify, send_file
import os
import re
import time

app = Flask(__name__)

CARPETA_SRT = os.path.join(os.path.dirname(__file__), 'archivos_srt')
os.makedirs(CARPETA_SRT, exist_ok=True)
app.config['CARPETA_SRT'] = CARPETA_SRT

historial_busquedas = []

@app.after_request
def permitir_acceso(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['X-Robots-Tag'] = 'all'
    return response

def normalizar_texto(texto):
    """Convierte a minúsculas, quita espacios extra, guiones, bajos y caracteres especiales"""
    if not texto: return ""
    t = texto.lower().strip()
    t = re.sub(r'[_\\/\-]+', ' ', t)       # Reemplaza _ - \ por espacios
    t = re.sub(r'\s+', ' ', t)              # Espacios múltiples → uno solo
    t = re.sub(r'[^\w\s]', '', t)           # Quita signos de puntuación
    return t.strip()

def descomponer_nombre_archivo(nombre):
    """Extrae artista y canción del nombre del archivo: Artista - Canción.srt"""
    sin_ext = nombre.replace('.srt', '').strip()
    if ' - ' in sin_ext:
        artista, cancion = sin_ext.split(' - ', 1)
    else:
        artista, cancion = 'Desconocido', sin_ext
    return {
        "archivo": nombre,
        "artista_original": artista.strip(),
        "cancion_original": cancion.strip(),
        "artista_norm": normalizar_texto(artista),
        "cancion_norm": normalizar_texto(cancion),
        "ruta": f"/descargar/{nombre}",
        "fecha": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(os.path.getmtime(os.path.join(CARPETA_SRT, nombre))))
    }

def leer_archivos_guardados():
    lista = []
    for nombre in os.listdir(CARPETA_SRT):
        if nombre.endswith('.srt'):
            lista.append(descomponer_nombre_archivo(nombre))
    return sorted(lista, key=lambda x: x['fecha'], reverse=True)

def coincidencias(consulta, canciones):
    """Busca coincidencias parciales y normalizadas"""
    q = normalizar_texto(consulta)
    resultados = []
    for c in canciones:
        # Coincidencia exacta parcial
        coincide_artista = q in c['artista_norm'] or c['artista_norm'] in q
        coincide_cancion = q in c['cancion_norm'] or c['cancion_norm'] in q
        # Palabras clave separadas
        palabras_q = set(q.split())
        palabras_a = set(c['artista_norm'].split() + c['cancion_norm'].split())
        palabras_comunes = len(palabras_q & palabras_a) / len(palabras_q) if palabras_q else 0
        
        if coincide_artista or coincide_cancion or palabras_comunes >= 0.5:
            resultados.append(c)
    return resultados

def obtener_recomendaciones(consulta=''):
    todas = leer_archivos_guardados()
    if not consulta:
        return todas[:5]
    return coincidencias(consulta, todas)[:5]

@app.route('/')
def index():
    recomendaciones = obtener_recomendaciones()
    return render_template('index.html', 
                           canciones=leer_archivos_guardados(), 
                           recomendaciones=recomendaciones)

@app.route('/api/buscar')
def buscar():
    q = request.args.get('q', '').strip()
    if q:
        historial_busquedas.append(q)
        if len(historial_busquedas) > 20:
            historial_busquedas.pop(0)
    
    todas = leer_archivos_guardados()
    resultados = coincidencias(q, todas) if q else todas
    
    return jsonify({
        "consulta": q,
        "encontrados": len(resultados),
        "resultados": resultados,
        "recomendaciones": obtener_recomendaciones(q)
    })

@app.route('/descargar/<nombre>')
def descargar(nombre):
    ruta = os.path.join(CARPETA_SRT, nombre)
    if not os.path.exists(ruta):
        return "Archivo no encontrado", 404
    return send_file(ruta, as_attachment=True)

@app.route('/api/lista')
def lista_api():
    return jsonify({
        "total": len(leer_archivos_guardados()),
        "formato_nombre": "Artista - Nombre de la canción.srt",
        "ejemplo_nombre": "DI BOWNS - SARCASMO SIN AUTOTUNE — GANGRENA MENTAL.srt",
        "canciones": leer_archivos_guardados(),
        "buscar": "/api/buscar?q=TU_CONSULTA",
        "descargar": "/descargar/NOMBRE_ARCHIVO.srt"
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)