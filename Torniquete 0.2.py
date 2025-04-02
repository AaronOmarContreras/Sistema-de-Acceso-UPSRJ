import gpiod
import time
import pymysql
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import os
import threading

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
def leer_estado_rele(ID1):
    conn = pymysql.connect(user="miusuario", password="10203040", host="localhost", database="estudiantes_upsrj")
    cursor = conn.cursor()
    cursor.execute(f"SELECT ID1 FROM estudiantes WHERE ID1 = '{ID1}'")
    datos = cursor.fetchall()
    conn.close()
    return any(dato[0] for dato in datos)

# Función para registrar el log de acceso
def registrar_log(ID1, tipo):
    try:
        conn = pymysql.connect(user="miusuario", password="10203040", host="localhost", database="estudiantes_upsrj")
        cursor = conn.cursor()
        # Se asume que existe una tabla 'registros' con las columnas: id, ID1, tipo, fecha
        query = "INSERT INTO registros (ID1, tipo_de_registro, fecha) VALUES (%s, %s, NOW())"
        cursor.execute(query, (ID1, tipo))
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
        query = "SELECT ID1, tipo_de_registro, fecha FROM registros ORDER BY fecha DESC"
        cursor.execute(query)
        registros = cursor.fetchall()
    except Exception as e:
        messagebox.showerror("Error", f"No se pudieron obtener los registros: {e}")
        return
    finally:
        conn.close()
    
    ventana_registros = tk.Toplevel()
    ventana_registros.title("Registros de Entrada y Salida")
    
    text_area = tk.Text(ventana_registros, width=80, height=20)
    text_area.pack(padx=10, pady=10)
    
    if registros:
        for reg in registros:
            text_area.insert(tk.END, f"ID: {reg[0]} - Tipo: {reg[1]} - Fecha: {reg[2]}\n")
    else:
        text_area.insert(tk.END, "No se encontraron registros.")
    
    text_area.config(state=tk.DISABLED)

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
            label_imagen.pack()
        else:
            tk.Label(ventana_info, text="Imagen no encontrada", fg="red").pack()
    else:
        messagebox.showerror("Error", "Estudiante no encontrado.")

# Función para activar relevador, registrar log y mostrar información del estudiante
def activar_rele_y_mostrar_info(ID1, tipo_rele):
    print(f"\n🔹 Recibido ID1: {ID1} desde {tipo_rele.upper()}")

    if leer_estado_rele(ID1):
        registrar_log(ID1, tipo_rele)
        if tipo_rele == "entrada":
            print("Activando relevador de ENTRADA")
            registrar_log(ID1, tipo_rele)
            relay_entrada_line.set_value(0)
        elif tipo_rele == "salida":
            print("Activando relevador de SALIDA")
            registrar_log(ID1, tipo_rele)
            relay_salida_line.set_value(0)

        mostrar_info_estudiante(ID1)

        time.sleep(4)  # Mantener el relevador activado por 4 segundos
        relay_entrada_line.set_value(1)
        relay_salida_line.set_value(1)
        print("Relevadores desactivados\n")
    else:
        messagebox.showerror("Acceso denegado", "ID no registrado en el sistema.")

# Función que detecta cuando el lector RFID inserta un código en el campo de entrada
def on_entry_change(event, tipo_rele):
    widget = event.widget  # Detecta en qué campo se ingresó el código
    ID1 = widget.get()
    
    if len(ID1) >= 10:  # Evita capturas incompletas
        print(f"📌 Código leído ({tipo_rele}): {ID1}")
        widget.after(100, widget.delete, 0, 'end')  # Limpia el campo
        thread = threading.Thread(target=activar_rele_y_mostrar_info, args=(ID1, tipo_rele))
        thread.start()

# Crear la interfaz gráfica en una sola ventana
root = tk.Tk()
root.title("Control de Acceso RFID (HID)")

# Sección de Entrada
frame_entrada = tk.Frame(root)
frame_entrada.pack(pady=10)

tk.Label(frame_entrada, text="Ingrese ID (Entrada):").pack()
ID1_entry_entrada = tk.Entry(frame_entrada)
ID1_entry_entrada.pack()
ID1_entry_entrada.focus_set()
ID1_entry_entrada.bind('<KeyRelease>', lambda event: on_entry_change(event, "entrada"))

# Sección de Salida
frame_salida = tk.Frame(root)
frame_salida.pack(pady=10)

tk.Label(frame_salida, text="Ingrese ID (Salida):").pack()
ID1_entry_salida = tk.Entry(frame_salida)
ID1_entry_salida.pack()
ID1_entry_salida.bind('<KeyRelease>', lambda event: on_entry_change(event, "salida"))

# Botón para mostrar registros de acceso
btn_registros = tk.Button(root, text="Ver Registros", command=mostrar_registros)
btn_registros.pack(pady=10)

print("\nSistema en funcionamiento... esperando lectura RFID.\n")

# Mantener la ejecución de la interfaz gráfica en el hilo principal
try:
    root.mainloop()
except KeyboardInterrupt:
    print("\nFinalizando programa.")
    relay_entrada_line.release()
    relay_salida_line.release()
