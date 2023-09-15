#!/tools/conda/envs/TelegramNotify/bin/python


import requests
import sys
import os
import datetime
import json
import argparse

def parse_config(fname):
    cwd=os.path.dirname(os.path.realpath(__file__))
    fully_qualified_fname=os.path.join(cwd,fname)
    f = open(fully_qualified_fname,'rt+')
    conf=json.load(f)
    f.close()
    return conf


def datetime_string():
    return datetime.datetime.now().strftime('%Y-%m-%d  %H:%M:%S')            
    

def send_alert(user_id,bot_token,message_string):
    payload_body={"chat_id":user_id,
                  "text": message_string}
    url='https://api.telegram.org/bot'+bot_token+'/sendMessage'
    p=requests.post(url,json=payload_body)
    print(json.dumps(p.json(),indent=1))


if __name__=='__main__':
    conf=parse_config('conf.json')
    argparser=argparse.ArgumentParser()
    argparser.add_argument("-m","--Message")
    args=argparser.parse_args()
    txt=datetime_string()+'\n\n'+args.Message
    print(datetime_string())
    print("")
    send_alert(conf['user_id'],conf['token'],txt)


