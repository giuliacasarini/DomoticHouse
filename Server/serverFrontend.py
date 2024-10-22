from flask import Flask, render_template, redirect, url_for
from flask_wtf import FlaskForm
from wtforms import IntegerField, SubmitField
from wtforms.validators import DataRequired
from flask_bootstrap import Bootstrap
import telebot
import threading

from server import Server

#FLASK

app = Flask(__name__)
app.config['SECRET_KEY'] = 'C2HWGVoMGfNTBsrYQg8EcMrdTimkZfAb' #flask secret key for forms sending
Bootstrap(app)

class IDForm(FlaskForm):
    id = IntegerField('Type your house ID to manage it', validators=[DataRequired()])
    submit = SubmitField('Submit')

@app.route("/", methods=['GET', 'POST']) #login page to select house id
def login():
    message=""
    form = IDForm()
    if form.validate_on_submit():

        id = form.id.data
        if id <= len(s.get_houses()): #if house id exists, redirect to house url
            form.id.data = ""
            return redirect( url_for('index', house_id=id) )
        else:
            message = "Selected ID is not valid. Please type a valid one."
    return render_template('login.html', form=form, message=message)


@app.route("/house/<house_id>") #return house page given house id
def index(house_id):
    global f_id 
    f_id = int(house_id)
    templateData = { #data to be printed on house page
      		'temperature'  : s.get_houses()[f_id-1].temperature,               
            'des_temperature'  : s.get_houses()[f_id-1].des_temperature,
      		'presence'  : s.get_houses()[f_id-1].presence,
      		'holiday'  : s.get_houses()[f_id-1].holiday,
		    'lights'  : s.get_houses()[f_id-1].lights,
            'windows'  : s.get_houses()[f_id-1].windows,
            'photoresistor'  : s.get_houses()[f_id-1].photoresistor
      	}
    return render_template('index.html', **templateData)
	
@app.route("/<deviceName>/<action>") #function to manage buttons on house page and do the corresponding actions
def action(deviceName, action):
    if deviceName == 'lights' and action == 'on':
        s.lights_on(f_id)
    if deviceName == 'lights' and action == 'off':
        s.lights_off(f_id)
    if deviceName == 'windows' and action == 'on':
        s.open_windows(f_id)
    if deviceName == 'windows' and action == 'off':
        s.close_windows(f_id)
    if deviceName == 'temperature' and action == '+':
        s.get_houses()[f_id-1].des_temperature += 1
    if deviceName == 'temperature' and action == '-':
        s.get_houses()[f_id-1].des_temperature -= 1
    if deviceName == 'holiday' and action == 'on':
       s.get_houses()[f_id-1].holiday = True
    if deviceName == 'presence' and action == 'on':
        s.get_houses()[f_id-1].presence = True

    templateData = {
        'temperature'  : s.get_houses()[f_id-1].temperature,
        'des_temperature'  : s.get_houses()[f_id-1].des_temperature,
        'presence'  : s.get_houses()[f_id-1].presence,
        'holiday'  : s.get_houses()[f_id-1].holiday,
        'lights'  : s.get_houses()[f_id-1].lights,
        'windows'  : s.get_houses()[f_id-1].windows,
        'photoresistor'  : s.get_houses()[f_id-1].photoresistor
    }
    return render_template('index.html', **templateData)

#BOT TELEGRAM

BOT_TOKEN = '5498718423:AAE76KlEt_aBdFcmzYlI0Rp3BZTqQxdqftY' #telegram bot secret token

bot = telebot.TeleBot(BOT_TOKEN)	


@bot.message_handler(commands=['start']) #when the bot is started, it asks for an house id to know which one he has to consider
def send_welcome(message):
	bot.reply_to(message, "Welcome to your house bot!")     
	text = "What is your house ID?"
	sent_msg = bot.send_message(message.chat.id, text, parse_mode="Markdown")
	bot.register_next_step_handler(sent_msg, set_id)

def set_id(message): #setting house id for next actions
    global t_id 
    t_id = int(message.text)
    bot.reply_to(message, "ID set")

@bot.message_handler(commands=['temperature']) #sending current house temperature
def send_temperature(message):
    bot.reply_to(message, s.get_houses()[t_id-1].temperature)
    
@bot.message_handler(commands=['set_temperature']) #setting desired temperature
def current_temperature(message):
    text = "What temperature you would like to set?"
    sent_msg = bot.send_message(message.chat.id, text, parse_mode="Markdown")
    bot.register_next_step_handler(sent_msg, set_temperature)
    
def set_temperature(message): 
    s.get_houses()[t_id-1].des_temperature = int(message.text)
    bot.reply_to(message, "Temperature set")

@bot.message_handler(commands=['set_presence']) #setting presence into the house
def set_presence(message):
      s.get_houses()[t_id-1].presence = bool(message.text)
      bot.reply_to(message, "Presence set")

@bot.message_handler(commands=['ligths_on']) #turning lights on
def on_lights(message):
    s.lights_on(t_id)
    bot.reply_to(message, "Lights on") 

@bot.message_handler(commands=['lights_off']) #turning lights off
def off_lights(message):
    s.lights_off(t_id)
    bot.reply_to(message, "Lights off") 

@bot.message_handler(commands=['open_windows']) #opening windows
def windows_open(message):
    s.open_windows(t_id)
    bot.reply_to(message, "Windows opened") 

@bot.message_handler(commands=['close_windows']) #closing windows
def windows_close(message):
    s.close_windows(t_id)
    bot.reply_to(message, "Windows closed") 

@bot.message_handler(commands=['holiday']) #setting holiday mode
def set_mode(message):
    s.get_houses()[t_id-1].holiday = True
    bot.reply_to(message, "Holiday mode set")

@bot.message_handler(func=lambda msg: True) #default for any other command received 
def echo_all(message):
    bot.reply_to(message, "Please type a valid command!")

if __name__ == '__main__':
    s=Server()
    
    tB = threading.Thread(target=bot.infinity_polling, args=())
    tB.start()

    tS = threading.Thread(target=s.loop, args=())
    tS.start()

    tF = threading.Thread(target=app.run(host='0.0.0.0', port=80, debug=False), args=())
    tF.start()
    

