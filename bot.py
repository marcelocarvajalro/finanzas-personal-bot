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

# --- SERVIDOR FALSO PARA RENDER ---
app = Flask('')


@app.route('/')
def home(): return "Bot Activo"


def run(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))


def keep_alive(): t = Thread(target=run); t.start()


# --- CONFIGURACIÓN ---
TOKEN = os.environ.get("TELEGRAM_TOKEN", "TU_TOKEN_SI_ES_LOCAL")
SHEET_NAME = "Finanzas_Bot_DB"

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
    if os.path.exists("credenciales.json"):
        creds = ServiceAccountCredentials.from_json_keyfile_name("credenciales.json", scope)
    else:
        key_dict = json.loads(os.environ["text_key"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(key_dict, scope)
    client = gspread.authorize(creds)
    return client.open(SHEET_NAME).sheet1


# --- LÓGICA DEL BOT (MODO DIAGNÓSTICO) ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🛠️ MODO DIAGNÓSTICO ACTIVO 🛠️\nIntenta registrar algo.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto_original = update.message.text
    print(f"DEBUG: Recibí '{texto_original}'")  # Esto sale en los logs de Render

    try:
        # 1. Limpieza agresiva
        texto = texto_original.lower().strip()

        # Eliminar el "+" si hay un espacio accidental ("+ 500" -> "+500")
        if texto.startswith("+ "):
            texto = texto.replace("+ ", "+", 1)

        # 2. Separar monto y descripción
        partes = texto.split(" ", 1)
        if len(partes) < 2:
            await update.message.reply_text(f"⚠️ Error de Formato.\nEntendí: '{texto}'\nNecesito: Monto Descripción")
            return

        monto_str = partes[0]
        descripcion = partes[1]

        # 3. Limpieza de basura en el número
        # Quitamos comas, simbolos de moneda y espacios invisibles
        monto_limpio = monto_str.replace(",", "").replace("¢", "").replace("$", "").strip()

        # 4. Conversión (Aquí es donde fallaba)
        try:
            if monto_limpio.startswith("+"):
                tipo = "Ingreso"
                monto = float(monto_limpio.replace("+", ""))
            else:
                tipo = "Gasto"
                monto = float(monto_limpio)
                if monto > 0: monto = monto * -1  # Asegurar negativo
        except ValueError:
            # Si falla aquí, le decimos al usuario EXACTAMENTE qué intentó leer
            await update.message.reply_text(
                f"🔍 ERROR DE LECTURA:\nIntenté leer el número: '{monto_limpio}'\nOriginal: '{monto_str}'\nRevisa si escribiste una letra o símbolo raro.")
            return

        # 5. Categoría
        categoria_detectada = "otros"
        for cat, keywords in CATEGORIAS.items():
            if any(keyword in descripcion for keyword in keywords):
                categoria_detectada = cat
                break

        # Hormiga
        es_hormiga = False
        if descripcion.strip().endswith(" h"):
            es_hormiga = True
            descripcion = descripcion[:-2]  # Quitar la h

        # 6. Guardar
        sheet = conectar_sheet()
        fila = [datetime.now().strftime("%Y-%m-%d"), datetime.now().strftime("%H:%M:%S"), descripcion, monto,
                categoria_detectada, tipo, es_hormiga]
        sheet.append_row(fila)

        await update.message.reply_text(f"💾 Guardado con éxito:\nMonto: {monto}\nCat: {categoria_detectada}")

    except Exception as e:
        await update.message.reply_text(f"🔥 Error Crítico: {e}")


if __name__ == '__main__':
    keep_alive()
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    application.run_polling()