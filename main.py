import gpiod
import time
import pymysql
import tkinter as tk
from tkinter import messagebox, ttk
from PIL import Image, ImageTk
import os
import threading
from evdev import InputDevice, categorize, ecodes, list_devices
from dotenv import load_dotenv

# --- Carga de variables de entorno ---
load_dotenv()
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_NAME = os.getenv("DB_NAME")
DB_HOST = os.getenv("DB_HOST")

# Carpeta de imágenes
CARPETA_IMAGENES = "/home/victor/Desktop/Control de acceso estudiantil UPSRJ/FOTOS Alumnos UPSRJ"

# --- Configuración de GPIO para relevadores ---
RELAY_ENTRADA_PIN = 17
RELAY_SALIDA_PIN = 27
chip = gpiod.Chip('gpiochip4')
relay_entrada_line = chip.get_line(RELAY_ENTRADA_PIN)
relay_salida_line = chip.get_line(RELAY_SALIDA_PIN)
relay_entrada_line.request(consumer="RelayEntrada", type=gpiod.LINE_REQ_DIR_OUT)
relay_salida_line.request(consumer="RelaySalida", type=gpiod.LINE_REQ_DIR_OUT)

# --- Funciones de base de datos ---
def obtener_datos_estudiante(ID1):
    conn = pymysql.connect(user=DB_USER, password=DB_PASS, host=DB_HOST, database=DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT Nombre, Carrera, MATRICULA FROM estudiantes WHERE ID1 = %s", (ID1,))
    datos = cursor.fetchone()
    conn.close()
    return datos


def validar_ID_de_acceso(ID1):
    conn = pymysql.connect(user=DB_USER, password=DB_PASS, host=DB_HOST, database=DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM estudiantes WHERE ID1 = %s", (ID1,))
    exists = cursor.fetchone() is not None
    conn.close()
    return exists


def registrar_log(ID1, tipo):
    datos = obtener_datos_estudiante(ID1)
    if datos:
        nombre, carrera, matricula = datos
    else:
        nombre, carrera, matricula = ("Desconocido", "Desconocida", "Desconocida")
    try:
        conn = pymysql.connect(user=DB_USER, password=DB_PASS, host=DB_HOST, database=DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO registros (ID1, tipo_de_registro, nombre, matricula, carrera, fecha) VALUES (%s,%s,%s,%s,%s,NOW())",
            (ID1, tipo, nombre, matricula, carrera)
        )
        conn.commit()
    except Exception as e:
        print("Error al registrar log:", e)
    finally:
        conn.close()


def mostrar_registros():
    try:
        conn = pymysql.connect(user=DB_USER, password=DB_PASS, host=DB_HOST, database=DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT matricula, nombre, carrera, tipo_de_registro, fecha FROM registros ORDER BY fecha DESC")
        registros = cursor.fetchall()
    except Exception as e:
        messagebox.showerror("Error", f"No se pudieron obtener los registros: {e}")
        return
    finally:
        conn.close()

    ventana_tabla = tk.Toplevel(root_entrada)
    ventana_tabla.title("Registros de Acceso")
    cols = ("matricula","nombre","carrera","tipo","fecha")
    tree = ttk.Treeview(ventana_tabla, columns=cols, show="headings")
    for c,text in zip(cols, ["Matrícula","Nombre","Carrera","Tipo","Fecha"]):
        tree.heading(c, text=text)
        tree.column(c, width=120)
    for reg in registros:
        tree.insert("", tk.END, values=reg)
    tree.pack(fill=tk.BOTH, expand=True)
    sb = ttk.Scrollbar(ventana_tabla, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=sb.set)
    sb.pack(side=tk.RIGHT, fill=tk.Y)

# --- RFID y relevadores ---
PROCESS_FLAG = False

def read_rfid(device_path, tipo_rele):
    dev = InputDevice(device_path)
    codigo = ""
    for event in dev.read_loop():
        if event.type == ecodes.EV_KEY and event.value == 1:
            key = categorize(event).keycode
            if isinstance(key, list): key = key[0]
            if key == "KEY_ENTER":
                if codigo:
                    root_entrada.after(0, activar_rele_y_mostrar_info, codigo, tipo_rele)
                    codigo = ""
            else:
                if key.startswith("KEY_"):
                    codigo += key[4:]


def activar_rele_y_mostrar_info(ID1, tipo_rele):
    global PROCESS_FLAG
    if PROCESS_FLAG: return
    PROCESS_FLAG = True
    entry_id_widget.config(state="disabled")
    try:
        if validar_ID_de_acceso(ID1):
            registrar_log(ID1, tipo_rele)
            if tipo_rele == "entrada":
                relay_entrada_line.set_value(1)
            else:
                relay_salida_line.set_value(1)
            mostrar_info_estudiante(ID1, tipo_rele)
            time.sleep(5)
            relay_entrada_line.set_value(0)
            relay_salida_line.set_value(0)
        else:
            messagebox.showerror("Acceso denegado", "ID no registrado.")
    except Exception as e:
        messagebox.showerror("Error", f"Procesando ID: {e}")
    finally:
        PROCESS_FLAG = False
        entry_id_widget.config(state="normal")


def mostrar_info_estudiante(ID1, tipo_rele):
    datos = obtener_datos_estudiante(ID1)
    ventana = tk.Toplevel(root_entrada if tipo_rele == "entrada" else root_salida)
    ventana.title(f"{tipo_rele.title()} — {ID1}")
    x_offset = 50 if tipo_rele=="entrada" else mitad_w + 50
    ventana.geometry(f"+{x_offset}+50")
    if datos:
        nombre,carrera,matricula = datos
        tk.Label(ventana, text=f"Nombre: {nombre}", font=("Arial",16)).pack(pady=5)
        tk.Label(ventana, text=f"Carrera: {carrera}", font=("Arial",14)).pack(pady=5)
        tk.Label(ventana, text=f"Matrícula: {matricula}", font=("Arial",14)).pack(pady=5)
        img_path = os.path.join(CARPETA_IMAGENES, f"0{matricula}.jpg")
        if os.path.exists(img_path):
            img = Image.open(img_path).resize((200,200))
            imgtk = ImageTk.PhotoImage(img)
            lbl = tk.Label(ventana, image=imgtk); lbl.image = imgtk; lbl.pack(pady=10)
        else:
            tk.Label(ventana, text="Imagen no encontrada", fg="red").pack()
    else:
        tk.Label(ventana, text="Estudiante no encontrado", fg="red").pack()
    ventana.after(8000, ventana.destroy)

# --- Detección automática de lectores RFID ---
def detectar_lectores_RFID(min_lectores=4):
    devs = [InputDevice(p) for p in list_devices()]
    paths = [d.path for d in devs if 'RFID' in d.name.upper()]
    if len(paths) < min_lectores:
        raise RuntimeError(f"Se detectaron {len(paths)} lectores; esperados {min_lectores}.")
    return paths[:min_lectores]

# --- Punto de inicio ---
if __name__ == "__main__":
    # Detectar lectores
    l_e1,l_e2,l_s1,l_s2 = detectar_lectores_RFID()
    # Crear ventanas
    root_entrada = tk.Tk()
    root_entrada.title("Control de Acceso UPSRJ — Entrada")
    root_entrada.update_idletasks()
    total_w = root_entrada.winfo_screenwidth()
    total_h = root_entrada.winfo_screenheight()
    mitad_w = total_w // 2
    root_entrada.geometry(f"{mitad_w}x{total_h}+0+0")
    # Frame Entrada
    frame_e = tk.Frame(root_entrada, padx=20, pady=20)
    frame_e.pack(fill=tk.BOTH, expand=True)
    tk.Label(frame_e, text="Insertar ID:", font=("Arial",14)).pack(pady=5)
    entry_id_widget = tk.Entry(frame_e, font=("Arial",14), width=30)
    entry_id_widget.pack(pady=5); entry_id_widget.focus()
    entry_id_widget.bind('<Return>', lambda e: activar_rele_y_mostrar_info(entry_id_widget.get(), tipo_combo.get()))
    tipo_combo = ttk.Combobox(frame_e, values=["entrada","salida"], state="readonly", font=("Arial",12), width=28)
    tipo_combo.current(0); tipo_combo.pack(pady=5)
    tk.Button(frame_e, text="Registrar Manual", command=lambda: activar_rele_y_mostrar_info(entry_id_widget.get(), tipo_combo.get()), font=("Arial",12)).pack(pady=10)
    tk.Button(frame_e, text="Ver Registros", command=mostrar_registros).pack(pady=5)
    # Ventana Salida
    root_salida = tk.Toplevel(root_entrada)
    root_salida.title("Control de Acceso UPSRJ — Salida")
    root_salida.geometry(f"{mitad_w}x{total_h}+{mitad_w}+0")
    frame_s = tk.Frame(root_salida, padx=20, pady=20)
    frame_s.pack(fill=tk.BOTH, expand=True)
    tk.Label(frame_s, text="Pantalla de Salida", font=("Arial",16)).pack(pady=10)

    # Iniciar threads RFID
    for path,tipo in [(l_e1,'entrada'),(l_e2,'entrada'),(l_s1,'salida'),(l_s2,'salida')]:
        threading.Thread(target=read_rfid, args=(path,tipo), daemon=True).start()

    # Ejecutar GUI
    print("Sistema en funcionamiento...")
    root_entrada.mainloop()
    # Liberar líneas GPIO al cerrar
    relay_entrada_line.release()
    relay_salida_line.release()
