import os
import openai
from flask import Flask
from flask import request, jsonify
import re
from flair.data import Sentence
from flair.models import SequenceTagger
import ast
import pandas as pd
from dotenv import load_dotenv
import os

load_dotenv()
# Get the value of a user environment variable
openai.api_type = os.getenv('API_TYPE')
openai.api_base = os.getenv('API_BASE')
openai.api_version = os.getenv('API_VERSION')
openai.api_key = os.getenv('API_KEY')

print("Started Importing the NER Model..")
tagger = SequenceTagger.load("flair/ner-english-ontonotes-large")
print("Completed Importing the NER Model..")

def validating_age(age_list):
    try:
        if len(age_list)!=0:
            age=int(age_list[0])
            if 0<age<100:
                print("Valid")
            else:
                age=''
        else:
            age = ''
        return age
    except Exception as e:
        print(e)
        return ''


def entitiy_extractor(text,tagger):
    try:
        ner_dict = []
        person_ner = False
        gpe_ner = False
        sentence = Sentence(text.lower())
        # predict NER tags
        tagger.predict(sentence)
        print(sentence.get_spans('ner'))
        # predict NER tags
        if len(sentence.get_spans('ner')) != 0:
            for entity in sentence.get_spans('ner'):
                    if entity.tag == 'PERSON':
                        ner_dict.append({'entity_group': entity.tag, 'word': entity.text})
                        person_ner=True
                    elif entity.tag == 'GPE':
                        ner_dict.append({'entity_group': entity.tag, 'word': entity.text})
                        gpe_ner = True
                    else:
                        person_ner=False
                        gpe_ner = False
        if gpe_ner==False and person_ner==False:
            no_person_name = {'entity_group': "PERSON", 'word': ""}
            no_location = {'entity_group': "GPE", 'word': ""}
            ner_dict.append(no_person_name)
            ner_dict.append(no_location)
        elif person_ner==False:
            no_person_name = {'entity_group': "PERSON", 'word': ""}
            ner_dict.append(no_person_name)
        else:
            no_location = {'entity_group': "GPE", 'word': ""}
            ner_dict.append(no_location)
        number_pattern="\+?\d[\d -]{8,12}\d"
        number_list = re.findall(number_pattern, text)
        if len(number_list)==0:
            number=""
        else:
            number=number_list[0]
        ner_dict.append({"entity_group":"Phone Number","word":number})
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails_found = re.findall(email_pattern, text)
        if len(emails_found)==0:
            emails_found=""
        else:
            emails_found=emails_found[0]
        ner_dict.append({"entity_group":"Email","word":emails_found})
        age_pattern = r'(?<!\d|\w)\d{2}(?!\d)'
        ages_found = re.findall(age_pattern, text)
        ages_found=validating_age(ages_found)
        ner_dict.append({"entity_group": "Age","word": ages_found})
        message_text = [{'role': 'system',
                         'content': "'{}' check the given conversation and find the correct spokeperson name entitie and give only python dict back with key 'name'".format(text.lower())}]
        completion = openai.ChatCompletion.create(
                engine="Test-Chatbot",
                messages=message_text,
                temperature=0.7,
                max_tokens=800,
                top_p=0.95,
                frequency_penalty=0,
                presence_penalty=0,
                stop=None
            )
        print(f"Assistant->{completion['choices'][0]['message']['content']}")
        print(ner_dict)
        try:
            chat_champletion_result=ast.literal_eval(completion['choices'][0]['message']['content'])
        except:
            chat_champletion_result={}

        # iterate over the list
        if len(chat_champletion_result)>0:
            for i in ner_dict:
                for ele in i:
                    if i[ele] == 'PERSON':
                        i['word'] = chat_champletion_result['name']
            Final_ner_result = []
            for dictionary in ner_dict:
                if dictionary not in Final_ner_result:
                    Final_ner_result.append(dictionary)
            return Final_ner_result
        else:
            return ner_dict
    except Exception as e:
        print(e)
        return


app = Flask(__name__)


@app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"

@app.route("/ner", methods=['POST'])
def entities():
    if request.method == 'POST':
        text = request.form['input']
        result=entitiy_extractor(text, tagger)
        column_names = [item['entity_group'] for item in result]
        column_values = [item['word'] for item in result]
        # Create a DataFrame using the extracted column names and values
        df = pd.DataFrame([column_values], columns=column_names)
        df.to_csv('Records.csv', mode='a', index=False, header=False)
    return jsonify(result),200


if __name__ == '__main__':
    app.run(port=4200)


