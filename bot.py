import logging
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from datetime import datetime
import os
import json
from flask import Flask
from threading import Thread

# --- 1. EL TRUCO PARA RENDER (SERVIDOR FALSO) ---
app = Flask('')


@app.route('/')
def home():
    return "¡Hola! Soy el bot de Marcelo y estoy vivo."


def run():
    # Render asigna un puerto en la variable PORT, usamos 8080 por defecto
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)


def keep_alive():
    t = Thread(target=run)
    t.start()


# --- 2. CONFIGURACIÓN DEL BOT ---
# Leemos el TOKEN desde los secretos (Variable de entorno)
# Si no existe (local), pégalo aquí para pruebas, pero en la nube lo leerá solo
TOKEN = os.environ.get("TELEGRAM_TOKEN", "TU_TOKEN_AQUI_SI_PRUEBAS_LOCAL")

SHEET_NAME = "Finanzas_Bot_DB"

# Categorías
CATEGORIAS = {
    "comida": ["almuerzo", "cena", "desayuno", "cafe", "café", "super", "mercado", "uber eats", "rappi"],
    "transporte": ["uber", "didi", "taxi", "bus", "tren", "gasolina", "parqueo", "peaje"],
    "salud": ["farmacia", "medicina", "doctor", "dentista", "hospital"],
    "salidas": ["cine", "bar", "birra", "fiesta", "entrada", "concierto"],
    "sinpe": ["sinpe"]
}


# --- 3. CONEXIÓN GOOGLE SHEETS (HÍBRIDA) ---
def conectar_sheet():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']

    if os.path.exists("credenciales.json"):
        creds = ServiceAccountCredentials.from_json_keyfile_name("credenciales.json", scope)
    else:
        # En Render leemos el secreto de la variable 'text_key'
        key_dict = json.loads(os.environ["text_key"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(key_dict, scope)

    client = gspread.authorize(creds)
    sheet = client.open(SHEET_NAME).sheet1
    return sheet


# --- 4. LÓGICA DEL BOT ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "¡Hola Marcelo! 🚀\n\nEstoy vivo en la nube.\n\nEjemplos:\n- Gasto: `5000 almuerzo`\n- Ingreso: `+200000 pago`\n- Hormiga: `2000 helado h`")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.lower().strip()
    fecha = datetime.now().strftime("%Y-%m-%d")
    hora = datetime.now().strftime("%H:%M:%S")
    es_hormiga = False
    tipo = "Gasto"

    try:
        if texto.endswith(" h"):
            es_hormiga = True
            texto = texto[:-2].strip()

        partes = texto.split(" ", 1)
        if len(partes) < 2:
            await update.message.reply_text("⚠️ Usa: `Monto Descripción`")
            return

        monto_str = partes[0]
        descripcion = partes[1]

        if monto_str.startswith("+"):
            tipo = "Ingreso"
            monto = float(monto_str.replace("+", ""))
        else:
            tipo = "Gasto"
            monto = float(monto_str) * -1

        categoria_detectada = "otros"
        for cat, keywords in CATEGORIAS.items():
            if any(keyword in descripcion for keyword in keywords):
                categoria_detectada = cat
                break
        if descripcion in CATEGORIAS.keys():
            categoria_detectada = descripcion

        sheet = conectar_sheet()
        fila = [fecha, hora, descripcion, monto, categoria_detectada, tipo, es_hormiga]
        sheet.append_row(fila)

        emoji = "🐜" if es_hormiga else "✅"
        await update.message.reply_text(f"{emoji} Guardado: ₡{monto:,.0f} ({categoria_detectada})")

    except ValueError:
        await update.message.reply_text("⚠️ El monto debe ser un número.")
    except Exception as e:
        logging.error(f"Error: {e}")
        await update.message.reply_text(f"❌ Error: {e}")


if __name__ == '__main__':
    # 1. Arrancamos el servidor falso en segundo plano
    keep_alive()

    # 2. Arrancamos el bot
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    print("🤖 Bot corriendo...")
    application.run_polling()