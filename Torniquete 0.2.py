import gpiod
import time
import pymysql
import tkinter as tk
from tkinter import messagebox, ttk
from PIL import Image, ImageTk
import os
import threading
from evdev import InputDevice, categorize, ecodes
from dotenv import load_dotenv
from USB_PORT_DEVICE_LISTING import obtener_lectores

load_dotenv()

DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_NAME = os.getenv("DB_NAME")
DB_HOST = os.getenv("DB_HOST")

CARPETA_IMAGENES = "/home/victor/Desktop/Control de acceso estudiantil UPSRJ/FOTOS Alumnos UPSRJ"
RELAY_ENTRADA_PIN = 17
RELAY_SALIDA_PIN = 27
chip = gpiod.Chip('gpiochip4')
relay_entrada_line = chip.get_line(RELAY_ENTRADA_PIN)
relay_salida_line = chip.get_line(RELAY_SALIDA_PIN)
relay_entrada_line.request(consumer="RelayEntrada", type=gpiod.LINE_REQ_DIR_OUT)
relay_salida_line.request(consumer="RelaySalida", type=gpiod.LINE_REQ_DIR_OUT)

def obtener_datos_estudiante(ID1):
    conn = pymysql.connect(user=DB_USER, password=DB_PASS, host=DB_HOST, database=DB_NAME)
    cursor = conn.cursor()
    cursor.execute(f"SELECT Nombre, Carrera, MATRICULA FROM estudiantes WHERE ID1 = '{ID1}'")
    datos_estudiante = cursor.fetchone()
    conn.close()
    return datos_estudiante

def validar_ID_de_acceso(ID1):
    conn = pymysql.connect(user=DB_USER, password=DB_PASS, host=DB_HOST, database=DB_NAME)
    cursor = conn.cursor()
    cursor.execute(f"SELECT ID1 FROM estudiantes WHERE ID1 = '{ID1}'")
    datos = cursor.fetchall()
    conn.close()
    return any(dato[0] for dato in datos)

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

def mostrar_info_estudiante(ID1, ventana):
    datos_estudiante = obtener_datos_estudiante(ID1)
    if datos_estudiante:
        nombre, carrera, matricula = datos_estudiante
        info_texto = f"Nombre: {nombre}\nCarrera: {carrera}\nMATRICULA: {matricula}"
        for widget in ventana.winfo_children():
            widget.destroy()
        tk.Label(ventana, text=info_texto, font=("Arial", 12)).pack()
        imagen_path = os.path.join(CARPETA_IMAGENES, f"{ID1}.jpg")
        if os.path.exists(imagen_path):
            img = Image.open(imagen_path).resize((200, 200))
            img = ImageTk.PhotoImage(img)
            label = tk.Label(ventana, image=img)
            label.image = img
            label.pack()
        else:
            tk.Label(ventana, text="Imagen no encontrada", fg="red").pack()

def activar_rele_y_mostrar_info(ID1, tipo_rele, ventana):
    print(f"\n Recibido ID1: {ID1} desde {tipo_rele.upper()}")
    if validar_ID_de_acceso(ID1):
        registrar_log(ID1, tipo_rele)
        if tipo_rele == "entrada":
            relay_entrada_line.set_value(1)
        elif tipo_rele == "salida":
            relay_salida_line.set_value(1)
        mostrar_info_estudiante(ID1, ventana)
        time.sleep(4)
        relay_entrada_line.set_value(0)
        relay_salida_line.set_value(0)
        print("Relevadores desactivados\n")
    else:
        tk.messagebox.showerror("Acceso denegado", "ID no registrado.")

def read_rfid(device_path, tipo_rele, ventana):
    dev = InputDevice(device_path)
    rfid_code = ""
    for event in dev.read_loop():
        if event.type == ecodes.EV_KEY and event.value == 1:
            key_event = categorize(event)
            key = key_event.keycode
            if isinstance(key, list):
                key = key[0]
            if key == "KEY_ENTER":
                if rfid_code:
                    print(f"RFID leído: {rfid_code}")
                    ventana.after(0, activar_rele_y_mostrar_info, rfid_code, tipo_rele, ventana)
                    rfid_code = ""
            elif key.startswith("KEY_"):
                rfid_code += key[4:]

# Crear dos ventanas: una por cada pantalla
ventana_entrada = tk.Tk()
ventana_entrada.geometry("600x400+0+0")
ventana_entrada.title("ENTRADAS")

ventana_salida = tk.Toplevel()
ventana_salida.geometry("600x400+1920+0")  # Ajusta según la posición de tu segundo monitor
ventana_salida.title("SALIDAS")

# Lanzar hilos RFID
lectores = obtener_lectores()
for lector in lectores.get("entrada", []):
    threading.Thread(target=read_rfid, args=(lector, "entrada", ventana_entrada), daemon=True).start()

for lector in lectores.get("salida", []):
    threading.Thread(target=read_rfid, args=(lector, "salida", ventana_salida), daemon=True).start()

print("\nSistema funcionando... esperando lectura RFID\n")

# Ejecutar ambas ventanas
ventana_entrada.mainloop()
