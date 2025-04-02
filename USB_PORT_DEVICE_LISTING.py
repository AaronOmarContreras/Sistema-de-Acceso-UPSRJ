from evdev import InputDevice, list_devices

dispositivos = [InputDevice(path) for path in list_devices()]
for dev in dispositivos:
    print(f"Path: {dev.path}")
    print(f"Nombre: {dev.name}")
    print(f"Físico: {dev.phys}")
    print("-" * 40)

# Script para listar dispositivos USB
# Este script lista todos los dispositivos USB conectados al sistema
# y muestra información relevante sobre cada uno de ellos.