import logging
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from datetime import datetime
import re

# --- CONFIGURACIÓN ---
TOKEN = "8541832197:AAHCbxj7N6Qq-oRzn987VFvfMFesdbmGJJ4"  # Tu token actual
SHEET_NAME = "Finanzas_Bot_DB"  # El nombre exacto de tu Sheet
JSON_CREDENTIALS = "credenciales.json"  # El nombre de tu archivo descargado

# Categorías y palabras clave simples para intentar adivinar
CATEGORIAS = {
    "comida": ["almuerzo", "cena", "desayuno", "cafe", "café", "super", "mercado", "uber eats", "rappi"],
    "transporte": ["uber", "didi", "taxi", "bus", "tren", "gasolina", "parqueo", "peaje"],
    "salud": ["farmacia", "medicina", "doctor", "dentista", "hospital"],
    "salidas": ["cine", "bar", "birra", "fiesta", "entrada", "concierto"],
    "sinpe": ["sinpe"]
}


# --- CONEXIÓN GOOGLE SHEETS ---
def conectar_sheet():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name(JSON_CREDENTIALS, scope)
    client = gspread.authorize(creds)
    sheet = client.open(SHEET_NAME).sheet1
    return sheet


# --- LÓGICA DEL BOT ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "¡Hola Marcelo! 🚀\n\nListo para registrar finanzas.\n\nEjemplos:\n- Gasto: `5000 almuerzo`\n- Ingreso: `+200000 pago`\n- Hormiga: `2000 helado h`")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.lower().strip()

    # Datos básicos
    fecha = datetime.now().strftime("%Y-%m-%d")
    hora = datetime.now().strftime("%H:%M:%S")
    es_hormiga = False
    tipo = "Gasto"

    try:
        # 1. Detectar si es Gasto Hormiga (termina en 'h')
        if texto.endswith(" h"):
            es_hormiga = True
            texto = texto[:-2].strip()  # Quitar la 'h' del texto

        # 2. Separar Monto y Descripción
        partes = texto.split(" ", 1)  # Divide en el primer espacio

        if len(partes) < 2:
            await update.message.reply_text("⚠️ Formato incorrecto. Usa: `Monto Descripción`")
            return

        monto_str = partes[0]
        descripcion = partes[1]

        # 3. Detectar si es Ingreso (+) o Gasto (-)
        if monto_str.startswith("+"):
            tipo = "Ingreso"
            monto = float(monto_str.replace("+", ""))
        else:
            tipo = "Gasto"
            monto = float(monto_str) * -1  # Gastos en negativo

        # 4. Categorización Automática
        categoria_detectada = "otros"

        # Buscar palabras clave en la descripción
        for cat, keywords in CATEGORIAS.items():
            if any(keyword in descripcion for keyword in keywords):
                categoria_detectada = cat
                break

        # Si la descripción es explícitamente una categoría (ej: "5000 transporte")
        if descripcion in CATEGORIAS.keys():
            categoria_detectada = descripcion

        # --- GUARDAR EN SHEETS ---
        sheet = conectar_sheet()
        # Orden columnas: fecha, hora, concepto, monto, categoria, tipo, es_hormiga
        fila = [fecha, hora, descripcion, monto, categoria_detectada, tipo, es_hormiga]
        sheet.append_row(fila)

        # Respuesta al usuario
        emoji = "🐜" if es_hormiga else "✅"
        await update.message.reply_text(
            f"{emoji} Registrado:\n"
            f"💰 {monto:,.0f}\n"
            f"🏷 {categoria_detectada.upper()}\n"
            f"📝 {descripcion}"
        )

    except ValueError:
        await update.message.reply_text("⚠️ El monto debe ser un número. Ejemplo: `4500 pizza`")
    except Exception as e:
        logging.error(f"Error: {e}")
        await update.message.reply_text(f"❌ Error interno: {e}")


if __name__ == '__main__':
    application = ApplicationBuilder().token(TOKEN).build()

    start_handler = CommandHandler('start', start)
    msg_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message)

    application.add_handler(start_handler)
    application.add_handler(msg_handler)

    print("🤖 Bot corriendo... (Presiona Ctrl+C para detener)")
    application.run_polling()