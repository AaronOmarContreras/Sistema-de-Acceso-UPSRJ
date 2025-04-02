import gpiod
import time
import pymysql
import tkinter as tk
from tkinter import messagebox, ttk
from PIL import Image, ImageTk
import os
import threading
from evdev import InputDevice, categorize, ecodes

# Ruta donde están almacenadas las imágenes de los estudiantes
CARPETA_IMAGENES = "/home/aaron-contreras/Documents/GitHub/Sistema-de-Acceso-UPSRJ/FOTOS Alumnos UPSRJ"

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
    conn = pymysql.connect(user="miusuario", password="10203040", host="localhost", database="estudiantes_upsrj")
    cursor = conn.cursor()
    cursor.execute(f"SELECT Nombre, Carrera, MATRICULA FROM estudiantes WHERE ID1 = '{ID1}'")
    datos_estudiante = cursor.fetchone()
    conn.close()
    return datos_estudiante

# Función para verificar si el ID1 está registrado
def validar_ID_de_acceso(ID1):
    conn = pymysql.connect(user="miusuario", password="10203040", host="localhost", database="estudiantes_upsrj")
    cursor = conn.cursor()
    cursor.execute(f"SELECT ID1 FROM estudiantes WHERE ID1 = '{ID1}'")
    datos = cursor.fetchall()
    conn.close()
    return any(dato[0] for dato in datos)

# Función para registrar el log de acceso
def registrar_log(ID1, tipo):

    if datos:
        nombre, carrera, matricula = datos
    else:
        nombre = "Desconocido"  
        carrera = "Desconocida"
        matricula = "Desconocida"
    try:
        conn = pymysql.connect(user="miusuario", password="10203040", host="localhost", database="estudiantes_upsrj")
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
        conn = pymysql.connect(user="miusuario", password="10203040", host="localhost", database="estudiantes_upsrj")
        cursor = conn.cursor()
        # Consulta para obtener los registros en el orden deseado
        query = "SELECT matricula, nombre, carrera, tipo_de_registro, fecha FROM registros ORDER BY fecha DESC"
        cursor.execute(query)
        registros = cursor.fetchall()
    except Exception as e:
        messagebox.showerror("Error", f"No se pudieron obtener los registros: {e}")
        return
    finally:
        conn.close()
    
    # Crear una nueva ventana para mostrar la tabla
    ventana_tabla = tk.Toplevel()
    ventana_tabla.title("Registros de Acceso")
    
    # Configurar el Treeview con las columnas deseadas
    columnas = ("matricula", "nombre", "carrera", "tipo", "fecha")
    tree = ttk.Treeview(ventana_tabla, columns=columnas, show="headings")
    
    # Definir los encabezados de columna
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
    
    # Insertar cada registro en el Treeview
    for reg in registros:
        tree.insert("", tk.END, values=reg)
    
    # Agregar el Treeview a la ventana y configurar scrollbar vertical
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

        # Buscar la imagen con el mismo ID
        imagen_path = os.path.join(CARPETA_IMAGENES, f"{ID1}.jpg")

        if os.path.exists(imagen_path):  # Verifica si la imagen existe
            img = Image.open(imagen_path)
            img = img.resize((200, 200))  # Redimensiona la imagen
            img = ImageTk.PhotoImage(img)

            label_imagen = tk.Label(ventana_info, image=img)
            label_imagen.image = img
            label_imagen.pack(padx=10, pady=10)

        else:
            tk.Label(ventana_info, text="Imagen no encontrada", fg="red").pack()
    else:
        messagebox.showerror("Error", "Estudiante no encontrado.")
# Función que detecta cuando el lector RFID inserta un código en el campo de entrada
def on_entry_change(event, tipo_rele):
    widget = event.widget  
    ID1 = widget.get()

    if len(ID1) >= 20:  
        widget.config(state="disabled")
        print(f" Código leído ({tipo_rele}): {ID1}")
        widget.after(100, widget.delete, 0, 'end')  
        

        thread = threading.Thread(target=activar_rele_y_mostrar_info, args=(ID1, tipo_rele))
        thread.start()

# Función para activar relevador, registrar log y mostrar información del estudiante
def activar_rele_y_mostrar_info(ID1, tipo_rele,widget):
    print(f"\n Recibido ID1: {ID1} desde {tipo_rele.upper()}")

    if validar_ID_de_acceso(ID1):
        registrar_log(ID1, tipo_rele)
        if tipo_rele == "entrada":
            print("Activando relevador de ENTRADA")
            relay_entrada_line.set_value(0)
        elif tipo_rele == "salida":
            print("Activando relevador de SALIDA")
            relay_salida_line.set_value(0)

        mostrar_info_estudiante(ID1)
        time.sleep(4)  
        relay_entrada_line.set_value(1)
        relay_salida_line.set_value(1)
        print("Relevadores desactivados\n")
    else:
        root.after(0, lambda: messagebox.showerror("Acceso denegado", "ID no registrado en el sistema."))

        root.after(0, lambda: widget.config(state="normal"))

def read_rfid(device_path, tipo_rele):
    dev = InputDevice(device_path)
    rfid_code = ""
    for event in dev.read_loop():
        if event.type == ecodes.EV_KEY and event.value == 1:  # Tecla presionada
            key_event = categorize(event)
            key = key_event.keycode
            # Algunos eventos pueden venir como lista, así que tomamos el primer elemento
            if isinstance(key, list):
                key = key[0]
            # Si se detecta la tecla ENTER, se asume fin de lectura
            if key == "KEY_ENTER":
                if len(rfid_code) > 0:
                    print(f"RFID leído desde {device_path}: {rfid_code}")
                    root.after(0, activar_rele_y_mostrar_info, rfid_code, tipo_rele)
                    rfid_code = ""
            else:
                # Convertir "KEY_#" a carácter
                if key.startswith("KEY_"):
                    key = key[4:]
                rfid_code += key

root = tk.Tk()
root.title("Control de Acceso RFID (HID)")
root.geometry("800x600")
root.minsize(500, 300)


# Sección de Entrada
frame_entrada = tk.Frame(root, padx=20, pady=20)
frame_entrada.pack(pady=10, fill="x")


tk.Label(frame_entrada, text="Ingrese ID (Entrada):").pack(anchor="w")
ID1_entry_entrada = tk.Entry(frame_entrada)
ID1_entry_entrada.pack(fill="x")
ID1_entry_entrada.focus_set()
#ID1_entry_entrada.bind('<KeyRelease>', lambda event: on_entry_change(event, "entrada"))

# Sección de Salida
frame_salida = tk.Frame(root, padx=20, pady=20)
frame_salida.pack(pady=10, fill="x")

tk.Label(frame_salida, text="Ingrese ID (Salida):").pack(anchor="w")
ID1_entry_salida = tk.Entry(frame_salida)
ID1_entry_salida.pack(fill="x")
ID1_entry_salida.focus_set()
#ID1_entry_salida.bind('<KeyRelease>', lambda event: on_entry_change(event, "salida"))

# Botón para mostrar registros de acceso
btn_registros = tk.Button(root, text="Ver Registros", command=mostrar_registros)
btn_registros.pack(pady=10)

lector_entrada_1 = "/dev/input/event3"
lector_entrada_2 = "/dev/input/event4"
lector_salida_1  = "/dev/input/event5"
lector_salida_2  = "/dev/input/event6"

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
