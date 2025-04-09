import gpiod
import time
import pymysql
import tkinter as tk
from tkinter import messagebox, ttk
from PIL import Image, ImageTk
import os
import threading
from evdev import InputDevice, categorize, ecodes

# --- Importación para cargar variables de entorno .env ---
from dotenv import load_dotenv
load_dotenv()
#---Globales---
PROCESS_FLAG = False

# --- Variables de conexión obtenidas desde archivo .env ---
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_NAME = os.getenv("DB_NAME")
DB_HOST = os.getenv("DB_HOST")

# Ruta donde están almacenadas las imágenes de los estudiantes
CARPETA_IMAGENES = "/home/victor/Desktop/Control de acceso estudiantil UPSRJ/FOTOS Alumnos UPSRJ"

# Configuración de GPIO para relevadores
RELAY_ENTRADA_PIN = 17
RELAY_SALIDA_PIN = 27
chip = gpiod.Chip('gpiochip4')
relay_entrada_line = chip.get_line(RELAY_ENTRADA_PIN)
relay_salida_line = chip.get_line(RELAY_SALIDA_PIN)
relay_entrada_line.request(consumer="RelayEntrada", type=gpiod.LINE_REQ_DIR_OUT)
relay_salida_line.request(consumer="RelaySalida", type=gpiod.LINE_REQ_DIR_OUT)

# Función para obtener datos del estudiante
def obtener_datos_estudiante(ID1):
    conn = pymysql.connect(user=DB_USER, password=DB_PASS, host=DB_HOST, database=DB_NAME)
    cursor = conn.cursor()
    cursor.execute(f"SELECT Nombre, Carrera, MATRICULA FROM estudiantes WHERE ID1 = '{ID1}'")
    datos_estudiante = cursor.fetchone()
    conn.close()
    return datos_estudiante

# Función para verificar si el ID1 está registrado
def validar_ID_de_acceso(ID1):
    conn = pymysql.connect(user=DB_USER, password=DB_PASS, host=DB_HOST, database=DB_NAME)
    cursor = conn.cursor()
    cursor.execute(f"SELECT ID1 FROM estudiantes WHERE ID1 = '{ID1}'")
    datos = cursor.fetchall()
    conn.close()
    return any(dato[0] for dato in datos)

# Función para registrar el log de acceso
def registrar_log(ID1, tipo):
    datos = obtener_datos_estudiante(ID1)
    if datos:
        nombre, carrera, matricula = datos
    else:
        nombre = "Desconocido"
        carrera = "Desconocida"
        matricula = "Desconocida"
    try:
        conn = pymysql.connect(user=DB_USER, password=DB_PASS, host=DB_HOST, database=DB_NAME)
        cursor = conn.cursor()
        query = "INSERT INTO registros (ID1, tipo_de_registro, nombre, matricula, carrera ,fecha) VALUES (%s, %s, %s, %s,%s ,NOW())"
        cursor.execute(query, (ID1, tipo, nombre, matricula, carrera))
        conn.commit()
    except Exception as e:
        print("Error al registrar log:", e)
    finally:
        conn.close()

# Función para mostrar registros de acceso
def mostrar_registros():
    try:
        conn = pymysql.connect(user=DB_USER, password=DB_PASS, host=DB_HOST, database=DB_NAME)
        cursor = conn.cursor()
        query = "SELECT matricula, nombre, carrera, tipo_de_registro, fecha FROM registros ORDER BY fecha DESC"
        cursor.execute(query)
        registros = cursor.fetchall()
    except Exception as e:
        messagebox.showerror("Error", f"No se pudieron obtener los registros: {e}")
        return
    finally:
        conn.close()

    ventana_tabla = tk.Toplevel()
    ventana_tabla.title("Registros de Acceso")

    columnas = ("matricula", "nombre", "carrera", "tipo", "fecha")
    tree = ttk.Treeview(ventana_tabla, columns=columnas, show="headings")

    tree.heading("matricula", text="Matrícula")
    tree.heading("nombre", text="Nombre")
    tree.heading("carrera", text="Carrera")
    tree.heading("tipo", text="Tipo")
    tree.heading("fecha", text="Fecha")

    tree.column("matricula", width=100)
    tree.column("nombre", width=200)
    tree.column("carrera", width=150)
    tree.column("tipo", width=100)
    tree.column("fecha", width=150)

    
    
    tree.pack(fill=tk.BOTH, expand=True)
    scrollbar = ttk.Scrollbar(ventana_tabla, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side="right", fill="y")

# Función para mostrar información e imagen del estudiante
def mostrar_info_estudiante(ID1):
    datos_estudiante = obtener_datos_estudiante(ID1)
    if datos_estudiante:
        nombre, carrera, matricula = datos_estudiante
        info_texto = f"Nombre: {nombre}\nCarrera: {carrera}\nMATRICULA: {matricula}"
        ventana_info = tk.Toplevel()
        ventana_info.title("Información del Estudiante")

        label_info = tk.Label(ventana_info, text=info_texto, font=("Arial", 12))
        label_info.pack()

        imagen_path = os.path.join(CARPETA_IMAGENES, f"0{matricula}.jpg")
        print(f'Ruta de imagen: {imagen_path}')
        if os.path.exists(imagen_path):
            img = Image.open(imagen_path)
            img = img.resize((200, 200))
            img = ImageTk.PhotoImage(img)

            label_imagen = tk.Label(ventana_info, image=img)
            label_imagen.image = img
            label_imagen.pack(padx=10, pady=10)
        else:
            tk.Label(ventana_info, text="Imagen no encontrada", fg="red").pack()

        ventana_info.after(10000, ventana_info.destroy)
    else:
        messagebox.showerror("Error", "Estudiante no encontrado.")

# Función que detecta cuando el lector RFID inserta un código en el campo de entrada
def on_entry_change(event):
    global PROCESS_FLAG
    if PROCESS_FLAG:
        return
    ID1 = entry_id.get()
    tipo_rele = tipo_combobox.get()
    if len(ID1) > 10:
        PROCESS_FLAG = True
        entry_id.config(state="disabled")
        print(f"Código leído ({tipo_rele}): {ID1}")
        thread = threading.Thread(target=activar_rele_y_mostrar_info, args=(ID1, tipo_rele))
      
        thread.start()

# Función para activar relevador, registrar log y mostrar información del estudiante
def activar_rele_y_mostrar_info(ID1, tipo_rele):
    global PROCESS_FLAG
    try:
        print(f"\n Recibido ID1: {ID1} desde {tipo_rele.upper()}")
        entry_id.delete(0,tk.END)
        entry_id.config(state="disabled")
        if validar_ID_de_acceso(ID1):
            registrar_log(ID1, tipo_rele)
            if tipo_rele == "entrada":
                print("Activando relevador de ENTRADA")
                relay_entrada_line.set_value(1)
            elif tipo_rele == "salida":
                print("Activando relevador de SALIDA")
                relay_salida_line.set_value(1)
            mostrar_info_estudiante(ID1)
            time.sleep(7)
            relay_entrada_line.set_value(0)
            relay_salida_line.set_value(0)
            print("Relevadores desactivados\n")
        else:
            root.after(0, lambda: messagebox.showerror("Acceso denegado", "ID no registrado en el sistema."))
            if entry_id is not None:
    
    
                root.after(0, lambda: entry_id.config(state="normal"))
    except Exception as e:
        root.after(0, lambda: messagebox.showerror("Error", f"Error al procesar el ID: {e}"))

    finally:
        PROCESS_FLAG = False
        root.after(0, lambda: entry_id.config(state="normal"))

    
    
# Función para leer el RFID desde el dispositivo
def read_rfid(device_path, tipo_rele):
    dev = InputDevice(device_path)
    rfid_code = ""
    for event in dev.read_loop():
        if event.type == ecodes.EV_KEY and event.value == 1:
            key_event = categorize(event)
            key = key_event.keycode
            if isinstance(key, list):
                key = key[0]
            if key == "KEY_ENTER":
                if len(rfid_code) > 0:
                    print(f"RFID leído desde {device_path}: {rfid_code}")
                    root.after(0, activar_rele_y_mostrar_info, rfid_code, tipo_rele)
                    rfid_code = ""
            else:
                if key.startswith("KEY_"):
                    key = key[4:]
                rfid_code += key


# --- Botón para registrar manualmente ---#
def registrar_manual():
    ID1 = entry_id.get()
    tipo_rele = tipo_combobox.get()
    if not ID1:
        messagebox.showerror("Error", "Por favor ingresa un ID válido.")
        return
    entry_id.delete(0, tk.END)
    root.after(0,activar_rele_y_mostrar_info, ID1, tipo_rele)


# --- Configuración de la interfaz gráfica --- #
root = tk.Tk()
root.title("Control de Acceso UPSRJ (RFID)")
root.geometry("800x600")
root.minsize(500, 300)

# --- Sección única de entrada de ID y tipo de acceso ---
frame_unico = tk.Frame(root, padx=30, pady=40)
frame_unico.pack(pady=30)

label_id = tk.Label(frame_unico, text="Insertar ID:", font=("Arial", 14))
label_id.pack(pady=(0,10))

entry_id = tk.Entry(frame_unico, font=("Arial", 14), width=30, relief="solid", bd=2)
entry_id.pack(pady=5)
entry_id.focus_set()
entry_id.bind('<KeyRelease>', on_entry_change)

tipo_combobox = ttk.Combobox(frame_unico, values=["entrada", "salida"], font=("Arial", 12), state="readonly", width=28)
tipo_combobox.current(0)
tipo_combobox.pack(pady=10)


btn_manual = tk.Button(frame_unico, text="Registrar Manualmente", command=registrar_manual, font=("Arial", 12), bg="#2196F3", fg="white", padx=10, pady=5)
btn_manual.pack(pady=10)

# Botón para mostrar registros de acceso
btn_registros = tk.Button(root, text="Ver Registros", command=mostrar_registros)
btn_registros.pack(pady=10)

lector_entrada_1 = "/dev/input/event10"
lector_entrada_2 = "/dev/input/event4"
lector_salida_1  = "/dev/input/event7"
lector_salida_2  = "/dev/input/event9"

threading.Thread(target=read_rfid, args=(lector_entrada_1, "entrada"), daemon=True).start()
threading.Thread(target=read_rfid, args=(lector_entrada_2, "entrada"), daemon=True).start()
threading.Thread(target=read_rfid, args=(lector_salida_1, "salida"), daemon=True).start()
threading.Thread(target=read_rfid, args=(lector_salida_2, "salida"), daemon=True).start()

print("\nSistema en funcionamiento... esperando lectura RFID.\n")

# Mantener la ejecución de la interfaz gráfica en el hilo principal
try:
    root.mainloop()
except KeyboardInterrupt:
    print("\nFinalizando programa.")
    relay_entrada_line.release()
    relay_salida_line.release()
