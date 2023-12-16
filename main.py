import subprocess

result = subprocess.run(['python', '-m', 'pip', 'install', 'pytelegrambotapi'],
                        capture_output=True,
                        text=True)

#pip.main(['install', 'pytelegrambotapi'])

import myBot
from flask import Flask

app = Flask('')


@app.route('/')
def home():
  if myBot.bot_check():
    return "I'm alive. Bot is checked"
  else:
    print("Problems with bot")


app.run(host='0.0.0.0', port=80)
