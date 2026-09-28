import shutil
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk


# Declaraciones

CARPETA_DESCARGAS = Path.home() / "Downloads"

archivos_ignorados = set()

ES_MAC = sys.platform == "darwin"

# Rejilla de 8 pt y márgenes de 20 pt
MARGEN = 20
ESPACIO_S = 4
ESPACIO_M = 8
ESPACIO_L = 16

ANCHO_CONTENIDO = 400
ALTO_BURBUJA = 28

ROJO_HOVER = "#e5484d"

# Transición claro <-> oscuro
DURACION_TRANSICION = 260  # ms
PASOS_TRANSICION = 14

TEMAS = {
    "claro": {
        "fondo": "#f5f5f7",
        "texto": "#1d1d1f",
        "secundario": "#6e6e73",
        "separador": "#d2d2d7",
        "burbuja": "#e6e6eb",
        "apagado": "#c7c7cc",
        "acento": "#d66020",
        "acento_hover": "#bd551b",
    },
    "oscuro": {
        "fondo": "#1e1e20",
        "texto": "#f5f5f7",
        "secundario": "#98989d",
        "separador": "#3a3a3c",
        "burbuja": "#3a3a3c",
        "apagado": "#636366",
        "acento": "#5b8fab",
        "acento_hover": "#7aa5bf",
    },
}

MODO_CTK = {"claro": "light", "oscuro": "dark"}


# Funciones

def detectar_tema():
    """En macOS respeta la apariencia del sistema; en otros sistemas, claro."""
    if ES_MAC:
        try:
            resultado = subprocess.run(
                ["defaults", "read", "-g", "AppleInterfaceStyle"],
                capture_output=True,
                text=True,
                timeout=2
            )
            if "Dark" in resultado.stdout:
                return "oscuro"
        except Exception:
            pass
    return "claro"


def mezclar(color_a, color_b, t):
    """Mezcla dos colores #rrggbb; t va de 0 (a) a 1 (b)."""
    a = [int(color_a[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(color_b[i:i + 2], 16) for i in (1, 3, 5)]
    r, g, bl = (round(x + (y - x) * t) for x, y in zip(a, b))
    return f"#{r:02x}{g:02x}{bl:02x}"


def icono_tema():
    # Muestra a qué modo se cambiará al hacer clic
    return "☀" if tema_actual == "oscuro" else "☾"


def ajustar_ventana():

    ventana.update_idletasks()

    escala = getattr(ventana, "_get_window_scaling", lambda: 1)()

    ancho = int(ventana.winfo_reqwidth() / escala)
    alto = int(ventana.winfo_reqheight() / escala)

    ventana.geometry(f"{ancho}x{alto}")


def recortar_texto(nombre, maximo):
    if fuente_burbuja.measure(nombre) <= maximo:
        return nombre

    recortado = nombre
    while recortado and fuente_burbuja.measure(recortado + "…") > maximo:
        recortado = recortado[:-1]

    return recortado + "…"


def crear_burbuja(fila, archivo, texto):

    burbuja = ctk.CTkButton(
        fila,
        text=texto,
        font=fuente_burbuja,
        width=fuente_burbuja.measure(texto) + 28,
        height=ALTO_BURBUJA,
        corner_radius=ALTO_BURBUJA // 2,
        border_width=0,
        fg_color=colores["burbuja"],
        hover_color=ROJO_HOVER,
        text_color=colores["texto"],
        bg_color=colores["fondo"],
        # Se retrasa un poco para que termine la animación del clic
        command=lambda: ventana.after(
            120, lambda: eliminar_archivo_ignorado(archivo)
        )
    )

    # Al pasar el mouse: fondo rojo (hover_color) y letras blancas
    burbuja.bind(
        "<Enter>",
        lambda evento: burbuja.configure(text_color="#ffffff"),
        add="+"
    )
    burbuja.bind(
        "<Leave>",
        lambda evento: burbuja.configure(text_color=colores["texto"]),
        add="+"
    )

    return burbuja


def actualizar_lista_ignorados():

    for fila in filas:
        fila.destroy()

    filas.clear()
    burbujas.clear()

    archivos = sorted(archivos_ignorados, key=lambda a: a.name.lower())

    if not archivos:
        etiqueta_vacia.pack(anchor="w")
        ajustar_ventana()
        return

    etiqueta_vacia.pack_forget()

    fila = None
    usado = 0

    for archivo in archivos:

        texto = recortar_texto(archivo.name, ANCHO_CONTENIDO - 28)
        ancho = fuente_burbuja.measure(texto) + 28

        if fila is None or usado + ancho > ANCHO_CONTENIDO:
            fila = ctk.CTkFrame(
                contenedor_burbujas,
                fg_color=colores["fondo"],
                corner_radius=0
            )
            fila.pack(anchor="w", pady=(0, ESPACIO_M))
            filas.append(fila)
            usado = 0

        burbuja = crear_burbuja(fila, archivo, texto)
        burbuja.pack(side="left", padx=(0, ESPACIO_M))
        burbujas.append(burbuja)

        usado += ancho + ESPACIO_M

    ajustar_ventana()


def nombre_disponible(carpeta, archivo):
    """Devuelve una ruta libre en la carpeta: images.jpeg -> images2.jpeg,
    images3.jpeg, y así sucesivamente."""

    destino = carpeta / archivo.name

    if not destino.exists():
        return destino

    numero = 2

    while True:
        destino = carpeta / f"{archivo.stem}{numero}{archivo.suffix}"

        if not destino.exists():
            return destino

        numero += 1


def organizar_descargas():

    if organizador_activo.get():

        for archivo in list(CARPETA_DESCARGAS.iterdir()):

            if not archivo.is_file():
                continue

            if archivo.name.startswith("."):
                continue

            if archivo in archivos_ignorados:
                continue

            extension = archivo.suffix

            if not extension:
                continue

            nombre_carpeta = extension[1:].upper()

            carpeta_destino = CARPETA_DESCARGAS / nombre_carpeta

            carpeta_destino.mkdir(exist_ok=True)

            destino = nombre_disponible(carpeta_destino, archivo)

            try:
                shutil.move(archivo, destino)
            except OSError:
                # Archivo en uso o aún descargándose: se reintenta después
                continue

    ventana.after(1000, organizar_descargas)


def seleccionar_archivos_ignorados():

    archivos = filedialog.askopenfilenames(
        title="Seleccionar archivos a ignorar",
        initialdir=CARPETA_DESCARGAS
    )

    for archivo in archivos:
        archivos_ignorados.add(Path(archivo))

    actualizar_lista_ignorados()


def eliminar_archivo_ignorado(archivo):

    archivos_ignorados.discard(archivo)

    actualizar_lista_ignorados()


def aplicar_colores():
    """Aplica la paleta actual (`colores`) a todos los widgets."""

    c = colores
    fondo = c["fondo"]

    ventana.configure(fg_color=fondo)

    for contenedor in (frame, cabecera, contenedor_burbujas, *filas):
        contenedor.configure(fg_color=fondo)

    separador.configure(fg_color=c["separador"])

    interruptor.configure(
        bg_color=fondo,
        fg_color=c["apagado"],
        progress_color=c["acento"],
        text_color=c["texto"]
    )

    boton_tema.configure(
        bg_color=fondo,
        text_color=c["secundario"],
        hover_color=c["burbuja"]
    )

    for etiqueta, clave in (
        (descripcion, "secundario"),
        (titulo_lista, "texto"),
        (ayuda, "secundario"),
        (etiqueta_vacia, "secundario"),
    ):
        etiqueta.configure(
            bg_color=fondo,
            fg_color=fondo,
            text_color=c[clave]
        )

    boton_ignorar.configure(
        bg_color=fondo,
        fg_color=c["acento"],
        hover_color=c["acento_hover"]
    )

    for burbuja in burbujas:
        burbuja.configure(
            bg_color=fondo,
            fg_color=c["burbuja"],
            text_color=c["texto"]
        )


def cambiar_tema():
    """Cambia claro <-> oscuro con una transición suave de colores."""

    global tema_actual, animando

    if animando:
        return

    animando = True

    origen = dict(colores)

    tema_actual = "claro" if tema_actual == "oscuro" else "oscuro"

    destino = TEMAS[tema_actual]

    boton_tema.configure(text=icono_tema())

    def paso(i):
        global animando

        t = i / PASOS_TRANSICION
        t = t * t * (3 - 2 * t)  # suavizado de entrada y salida

        for clave in destino:
            colores[clave] = mezclar(origen[clave], destino[clave], t)

        aplicar_colores()

        if i < PASOS_TRANSICION:
            ventana.after(DURACION_TRANSICION // PASOS_TRANSICION, paso, i + 1)
        else:
            animando = False
            ctk.set_appearance_mode(MODO_CTK[tema_actual])

    paso(1)


# Interfaz

tema_actual = detectar_tema()

colores = dict(TEMAS[tema_actual])

animando = False

ctk.set_appearance_mode(MODO_CTK[tema_actual])

ventana = ctk.CTk(fg_color=colores["fondo"])

ventana.title("Organizador de descargas")

organizador_activo = tk.IntVar(
    master=ventana,
    value=1
)

filas = []
burbujas = []


# Fuentes

fuente_principal = ctk.CTkFont(size=15, weight="bold")
fuente_titulo = ctk.CTkFont(size=13, weight="bold")
fuente_secundaria = ctk.CTkFont(size=12)
fuente_burbuja = ctk.CTkFont(size=13)
fuente_boton = ctk.CTkFont(size=13, weight="bold")
fuente_icono = ctk.CTkFont(size=18)


frame = ctk.CTkFrame(
    ventana,
    fg_color=colores["fondo"],
    corner_radius=0
)

frame.pack(fill="both", expand=True, padx=MARGEN, pady=MARGEN)


# Cabecera: interruptor, título en negrita e icono de tema en la esquina

cabecera = ctk.CTkFrame(
    frame,
    fg_color=colores["fondo"],
    corner_radius=0
)

cabecera.pack(fill="x")

interruptor = ctk.CTkSwitch(
    cabecera,
    text="Organizar descargas automáticamente",
    font=fuente_principal,
    variable=organizador_activo,
    onvalue=1,
    offvalue=0,
    width=44,
    switch_width=44,
    switch_height=24,
    button_color="#ffffff",
    button_hover_color="#ffffff",
    progress_color=colores["acento"],
    fg_color=colores["apagado"],
    text_color=colores["texto"],
    bg_color=colores["fondo"]
)

interruptor.pack(side="left")

boton_tema = ctk.CTkButton(
    cabecera,
    text=icono_tema(),
    font=fuente_icono,
    width=32,
    height=32,
    corner_radius=16,
    fg_color="transparent",
    hover_color=colores["burbuja"],
    text_color=colores["secundario"],
    bg_color=colores["fondo"],
    command=cambiar_tema
)

boton_tema.pack(side="right")


descripcion = ctk.CTkLabel(
    frame,
    text="Los archivos nuevos de Descargas se moverán a carpetas según su extensión.",
    font=fuente_secundaria,
    text_color=colores["secundario"],
    fg_color=colores["fondo"],
    wraplength=ANCHO_CONTENIDO - 54,
    justify="left",
    anchor="w"
)

# Sangría para alinear el texto con el del interruptor
descripcion.pack(anchor="w", padx=(54, 0), pady=(ESPACIO_S, 0))


# Separador

separador = ctk.CTkFrame(
    frame,
    height=1,
    corner_radius=0,
    fg_color=colores["separador"]
)

separador.pack(fill="x", pady=ESPACIO_L + ESPACIO_S)


# Sección: archivos ignorados (burbujas, sin cuadro)

titulo_lista = ctk.CTkLabel(
    frame,
    text="Archivos ignorados",
    font=fuente_titulo,
    text_color=colores["texto"],
    fg_color=colores["fondo"],
    anchor="w"
)

titulo_lista.pack(anchor="w")

ayuda = ctk.CTkLabel(
    frame,
    text="Haz clic en un archivo para quitarlo de la lista.",
    font=fuente_secundaria,
    text_color=colores["secundario"],
    fg_color=colores["fondo"],
    anchor="w"
)

ayuda.pack(anchor="w", pady=(ESPACIO_S, 0))


contenedor_burbujas = ctk.CTkFrame(
    frame,
    fg_color=colores["fondo"],
    corner_radius=0
)

contenedor_burbujas.pack(fill="x", pady=(ESPACIO_L, 0))

etiqueta_vacia = ctk.CTkLabel(
    contenedor_burbujas,
    text="Ningún archivo ignorado todavía",
    font=fuente_secundaria,
    text_color=colores["secundario"],
    fg_color=colores["fondo"],
    anchor="w"
)


# Botón en forma de píldora, alineado a la derecha

boton_ignorar = ctk.CTkButton(
    frame,
    text="Seleccionar archivos…",
    font=fuente_boton,
    width=190,
    height=36,
    corner_radius=18,
    fg_color=colores["acento"],
    hover_color=colores["acento_hover"],
    text_color="#ffffff",
    bg_color=colores["fondo"],
    command=seleccionar_archivos_ignorados
)

boton_ignorar.pack(anchor="e", pady=(ESPACIO_L + ESPACIO_S, 0))


# Atajo de teclado estándar de macOS: ⌘W cierra la ventana

if ES_MAC:
    ventana.bind("<Command-w>", lambda evento: ventana.destroy())


# Contenido inicial y tamaño de la ventana

actualizar_lista_ignorados()

ventana.resizable(False, False)


# Iniciar automáticamente

organizar_descargas()

ventana.mainloop()