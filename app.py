import os
import datetime
import requests
import gspread
import threading
import pytz
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, CommandHandler, CallbackQueryHandler, ContextTypes, filters
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# ==========================================
# CONFIGURATION & KEYS (Pulled from HF Secrets)
# ==========================================
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
WEATHER_API_KEY = os.environ.get("WEATHER_API_KEY")
CITY = "Singapore" 
GOOGLE_SHEET_URL_OR_ID = os.environ.get("GOOGLE_SHEET_URL_OR_ID")

# Timezone setup for accurate scheduling
SGT = pytz.timezone('Asia/Singapore')

# ==========================================
# GLOBAL STATE VARIABLES
# ==========================================
workout_counts = {
    "upper_pull": 0,
    "upper_push": 0,
    "legs": 0,
    "cardio": 0
}

wellbeing_state = {} 
wellbeing_responses = {"mental": "", "emotional": "", "physical": ""}

# ==========================================
# FLASK KEEP-ALIVE (For UptimeRobot)
# ==========================================
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is alive and running!"

def run_flask():
    # Hugging Face exposes port 7860
    app.run(host="0.0.0.0", port=7860)

# ==========================================
# API HELPER FUNCTIONS
# ==========================================
def get_weather():
    url = f"http://api.openweathermap.org/data/2.5/weather?q={CITY}&appid={WEATHER_API_KEY}&units=metric"
    try:
        res = requests.get(url).json()
        temp = res['main']['temp']
        desc = res['weather'][0]['description']
        return f"Weather: {temp}°C, {desc.title()}"
    except Exception:
        return "Could not fetch weather."

def get_calendar_events():
    SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
    try:
        creds = Credentials.from_service_account_file('credentials.json', scopes=SCOPES)
        service = build('calendar', 'v3', credentials=creds)
        
        now = datetime.datetime.now(SGT).isoformat()
        end_of_day = (datetime.datetime.now(SGT) + datetime.timedelta(days=1)).replace(hour=0, minute=0, second=0).isoformat()
        
        events_result = service.events().list(calendarId='primary', timeMin=now, timeMax=end_of_day,
                                              singleEvents=True, orderBy='startTime').execute()
        events = events_result.get('items', [])
        
        if not events:
            return "No upcoming events for today."
        
        event_list = "Today's Schedule:\n"
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            time_str = start[11:16] if 'T' in start else "All Day"
            event_list += f"- {time_str}: {event['summary']}\n"
        return event_list
    except Exception as e:
        return f"Calendar fetch error: {e}"

def log_to_sheets(mental, emotional, physical):
    try:
        gc = gspread.service_account(filename='credentials.json')
        sh = gc.open_by_key(GOOGLE_SHEET_URL_OR_ID)
        worksheet = sh.sheet1 
        
        date_str = datetime.datetime.now(SGT).strftime("%Y-%m-%d")
        worksheet.append_row([date_str, mental, emotional, physical])
        return True
    except Exception as e:
        print(f"Sheets Error: {e}")
        return False

# ==========================================
# SCHEDULED JOBS & COMMANDS
# ==========================================
async def morning_briefing(context: ContextTypes.DEFAULT_TYPE):
    weather = get_weather()
    calendar = get_calendar_events()
    message = f"🌅 Good Morning!\n\n{weather}\n\n{calendar}"
    await context.bot.send_message(chat_id=CHAT_ID, text=message)

async def trigger_wellbeing_check(context: ContextTypes.DEFAULT_TYPE):
    global wellbeing_state
    wellbeing_state['current_question'] = 'mental'
    await context.bot.send_message(chat_id=CHAT_ID, text="Time for a check-in. How is your Mental wellbeing?")

async def send_workout_checklist(context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton(f"Upper Body Pull: {workout_counts['upper_pull']}", callback_data='upper_pull')],
        [InlineKeyboardButton(f"Upper Body Push: {workout_counts['upper_push']}", callback_data='upper_push')],
        [InlineKeyboardButton(f"Legs: {workout_counts['legs']}", callback_data='legs')],
        [InlineKeyboardButton(f"Cardio: {workout_counts['cardio']}", callback_data='cardio')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(chat_id=CHAT_ID, text="🏋️ Workout Checklist:", reply_markup=reply_markup)

async def reset_weekly_counters(context: ContextTypes.DEFAULT_TYPE):
    global workout_counts
    for key in workout_counts:
        workout_counts[key] = 0
    await context.bot.send_message(chat_id=CHAT_ID, text="🔄 Weekly workout counters have been reset.")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.message.chat_id) != str(CHAT_ID): return
    await update.message.reply_text("👋 Bot started! I am ready to track your schedule, well-being, and workouts.")

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global wellbeing_state
    if str(update.message.chat_id) != str(CHAT_ID): return
    wellbeing_state['current_question'] = None
    await update.message.reply_text("🚫 Current action canceled. State reset.")

async def manual_workout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.message.chat_id) != str(CHAT_ID): return
    keyboard = [
        [InlineKeyboardButton(f"Upper Body Pull: {workout_counts['upper_pull']}", callback_data='upper_pull')],
        [InlineKeyboardButton(f"Upper Body Push: {workout_counts['upper_push']}", callback_data='upper_push')],
        [InlineKeyboardButton(f"Legs: {workout_counts['legs']}", callback_data='legs')],
        [InlineKeyboardButton(f"Cardio: {workout_counts['cardio']}", callback_data='cardio')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🏋️ Manual Workout Log:", reply_markup=reply_markup)

# ==========================================
# MESSAGE & BUTTON HANDLERS
# ==========================================
async def handle_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global wellbeing_state, wellbeing_responses
    if str(update.message.chat_id) != str(CHAT_ID): return

    text = update.message.text
    state = wellbeing_state.get('current_question')

    if state == 'mental':
        wellbeing_responses['mental'] = text
        wellbeing_state['current_question'] = 'emotional'
        await update.message.reply_text("Got it. How is your Emotional wellbeing?")
    elif state == 'emotional':
        wellbeing_responses['emotional'] = text
        wellbeing_state['current_question'] = 'physical'
        await update.message.reply_text("Noted. Finally, how is your Physical wellbeing?")
    elif state == 'physical':
        wellbeing_responses['physical'] = text
        wellbeing_state['current_question'] = None 
        success = log_to_sheets(wellbeing_responses['mental'], wellbeing_responses['emotional'], wellbeing_responses['physical'])
        if success:
            await update.message.reply_text("✅ Check-in complete and logged to Google Sheets.")
        else:
            await update.message.reply_text("❌ Failed to log to Sheets. Check console for errors.")

async def button_click_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    workout_type = query.data
    workout_counts[workout_type] += 1
    
    keyboard = [
        [InlineKeyboardButton(f"Upper Body Pull: {workout_counts['upper_pull']}", callback_data='upper_pull')],
        [InlineKeyboardButton(f"Upper Body Push: {workout_counts['upper_push']}", callback_data='upper_push')],
        [InlineKeyboardButton(f"Legs: {workout_counts['legs']}", callback_data='legs')],
        [InlineKeyboardButton(f"Cardio: {workout_counts['cardio']}", callback_data='cardio')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text="🏋️ Workout Checklist:", reply_markup=reply_markup)

# ==========================================
# MENU BUILDER & MAIN EXECUTION
# ==========================================
async def post_init(application: Application):
    await application.bot.set_my_commands([
        ("start", "Start the bot"),
        ("cancel", "Cancel current action"),
        ("workout", "Log a manual workout")
    ])

def main():
    threading.Thread(target=run_flask, daemon=True).start()
    application = Application.builder().token(TELEGRAM_TOKEN).post_init(post_init).build()

    jq = application.job_queue
    jq.run_daily(morning_briefing, time=datetime.time(hour=8, minute=0, tzinfo=SGT))
    jq.run_daily(trigger_wellbeing_check, time=datetime.time(hour=9, minute=0, tzinfo=SGT))
    jq.run_daily(trigger_wellbeing_check, time=datetime.time(hour=14, minute=0, tzinfo=SGT))
    jq.run_daily(trigger_wellbeing_check, time=datetime.time(hour=20, minute=0, tzinfo=SGT))
    jq.run_daily(send_workout_checklist, time=datetime.time(hour=20, minute=30, tzinfo=SGT))
    jq.run_daily(reset_weekly_counters, time=datetime.time(hour=23, minute=59, tzinfo=SGT), days=(6,))

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("cancel", cancel_command))
    application.add_handler(CommandHandler("workout", manual_workout))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_messages))
    application.add_handler(CallbackQueryHandler(button_click_handler))

    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()