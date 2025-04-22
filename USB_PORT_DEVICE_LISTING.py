from evdev import InputDevice, list_devices

# Ajusta estos nombres según cómo se llaman tus lectores en el sistema
NOMBRE_ENTRADA = "USB Entrada"
NOMBRE_SALIDA = "USB Salida"

def obtener_lectores():
    dispositivos = [InputDevice(path) for path in list_devices()]
    lectores = {"entrada": [], "salida": []}

    for dev in dispositivos:
        if NOMBRE_ENTRADA.lower() in dev.name.lower():
            lectores["entrada"].append(dev.path)
        elif NOMBRE_SALIDA.lower() in dev.name.lower():
            lectores["salida"].append(dev.path)

    return lectores


# Script para listar dispositivos USB
# Este script lista todos los dispositivos USB conectados al sistema
# y muestra información relevante sobre cada uno de ellos.