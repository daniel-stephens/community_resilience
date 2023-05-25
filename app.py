from flask import Flask, request, render_template, url_for, redirect, flash, session
import numpy as np
import pandas as pd
from .tools import *
import json
from flask_session import Session
from xml.dom import minidom
import requests
import time
import datetime
import os
import ast


received_data = json.load(open('dataset.json'))




os.urandom(24).hex()

topic_list = json.load(open('topic_list.json'))
all_texts = json.load(open("newsgroup_sub_500.json"))
# url = 'https://nist-topic-model.umiacs.umd.edu'
url = "http://54.87.190.90:5001"

global predicitons
predictions = []


app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24).hex()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)


## uSER FIRST LOGS IN

@app.route("/")
def home():
    return redirect(url_for("login"))


@app.route("/login", methods=["POST", "GET"])
def login():
    if request.method =="POST":
        with open('.\\static\\users\\users.json') as user_file:
            name_string = user_file.read()
            names = json.loads(name_string)
        name = request.form["name"]
        session["name"] = name
        

        if name in list(names.keys()):
            session["name"] = names[name]['username']
            session["labels"] = names[name]["labels"]
            session["user_id"] = names[name]["id"]
            session["labelled_document"] = names[name]["labelled_document"]
            user_id = session["user_id"]
            print('user id is {}'.format(user_id))
            return redirect(url_for("active_check", name=name))
            
        else:
            user = requests.post(url + "//create_user", {"user_session": name})
            user_id = user.json()["user_id"] 
            session["user_id"] = user_id
            session["labels"] = ""
            session["labelled_document"] = ""
            data = {
                "username": name, 
                "id" : user_id,
                "labels" : session["labels"],
                "labelled_document" : session["labelled_document"]
            }

            session["user_id"] = user_id  
            names[name]=data
            
            with open('.\\static\\users\\users.json', mode='w', encoding='utf-8') as name_json:
                # names = json.loads(name_string)
                names[name] = data
                json.dump(names, name_json, indent=4)

            
            
            return redirect(url_for("home_page", name=name, user_id=user_id))
    return render_template("login.html") 




# READING WHAT THE STUDY IS ABOUT
@app.route("//firstpage//<name>/", methods = ["POST", "GET"])
def home_page(name):
    if session.get("name") != name:
        # if not there in the session then redirect to the login page
        return redirect("/login")
    if request.method =="POST":
        return redirect(url_for("active_check", name=name))
    return render_template("first.html", name=name)



@app.route("//checkactive//<name>//", methods=["POST", 'GET'])
def active_check(name):
    if session.get("name") != name:
        # if not there in the session then redirect to the login page
        return redirect("/login")

    get_topic_list = url + "//get_topic_list"
    topics = requests.post(get_topic_list, json={
                            "user_id": session['user_id']
                            }).json()
    if len(topics["cluster"].keys()) == 1:
        return redirect(url_for("active_list", name=name))
    else:
        return redirect(url_for("non_active_list", name=name))





@app.route("//active_list//<name>", methods=["POST", "GET"])
def active_list(name):
    if session.get("name") != name:
    # if not there in the session then redirect to the login page
        return redirect("/login")

    get_topic_list = url + "//get_topic_list"
    topics = requests.post(get_topic_list, json={
                            "user_id": session['user_id']
                            }).json()

    rec = str(topics["document_id"])
    docs = list(set(session["labelled_document"].strip(",").split(",")))
    print(docs)

    results = get_single_document(topics["cluster"]["1"], all_texts, docs)

    if request.method =="POST":
        return redirect(url_for("finish"))
 
    return render_template("active_list.html", results=results, name=name, rec = rec)

    

 
 
@app.route("//non_active_list//<name>", methods=["POST", "GET"])
def non_active_list(name):
    if session.get("name") != name:
        # if not there in the session then redirect to the login page
        return redirect("/login")

    get_topic_list = url + "//get_topic_list"
        # print(session)
    topics = requests.post(get_topic_list, json={
                            "user_id": session['user_id']
                            }).json()

    recommended = int(topics["document_id"])

    docs = list(set(session["labelled_document"].strip(",").split(",")))
    print(docs)

    results = get_texts(topic_list=topics, all_texts=all_texts, docs=docs)

    sliced_results = get_sliced_texts(topic_list=topics, all_texts=all_texts)
    # print(sliced_results)

    keywords = topics["keywords"] 
    # print(keywords)

    if request.method =="POST":
        return redirect(url_for("finish"))

    return render_template("nonactive.html",sliced_results=sliced_results, results=results, name=name, keywords=keywords, recommended=recommended, document_list = topics["cluster"])



@app.route("//active//<name>//<document_id>/", methods=["GET", "POST"])
def active(name, document_id):
    get_topic_list = url + "//get_topic_list"

    topics = requests.post(get_topic_list, json={
                            "user_id": session['user_id']
                            }).json()
    # docs = list(set(session["labelled_document"].strip(",").split(",")))
    # results = get_texts(topic_list=topics, all_texts=all_texts, docs=docs)
    text = all_texts["text"][str(document_id)]
    print("start time")
    st =time.time()
    print(st)
    labels = list(set(session["labels"].strip(",").split(",")))

    if request.method =="POST":
        label = request.form.get("label")
        drop = request.form.get("suggestion")
        if label and drop:
            flash("Select either dropdown or type a label ")
            return render_template("activelearning.html", text =text, predictions=labels ) 
        
        if not label and not drop:
            flash("Select either dropdown or type a label ")
            return render_template("activelearning.html", text =text, predictions=labels ) 

        name=name
        document_id=document_id
        user_id = session["user_id"]
        et = time.time()
        print("end time")
        print(et)
        response_time = st- et

        

        save_response(name, label, response_time, document_id, user_id)
        recommend_document = url + "//recommend_document"
        posts = requests.post(recommend_document, json={
        "user_id" : int(user_id),
        "label": label,
        "response_time": response_time,
        "document_id" : document_id}).json()
        next = posts["document_id"]
        # print(posts.keys())
        predictions.append(label.lower()) 
        
        # session["labelled_document"] = session["labelled_document"]+","+str(document_id)
        session["labels"] = session["labels"] + "," + label
        labels = list(set(session["labels"].strip(",").split(",")))

        session["labelled_document"] = session["labelled_document"]+","+str(document_id)
        # print(session)
        # print([x.strip("") for x in session["labels"].split(",")])
        # print([x.strip("") for x in session["labelled_document"].split(",")])
        save_labels(session)
        return redirect(url_for("active", name=name, document_id=next, predictions=labels))
    return render_template("activelearning.html", text =text, predictions=labels ) 

    

 


### lABELLING THE TOPIC AND SAVING THE RESPONSE aaa
@app.route("//get_label//<document_id>//", methods=["POST", 'GET'])
def get_label(document_id):
    document_id = document_id 
    user_id=session["user_id"] 
    get_document_information = url + "//get_document_information"
    data = requests.post(get_document_information, json={ "document_id": document_id,
                                                        "user_id":user_id
                                                         }).json()
                                                         
    return redirect( url_for("label", response=data, name=session["name"], document_id=document_id))
    




@app.route("/logout", methods=["POST", "GET"])
def finish():
    name = session['name']
    session.pop(name, None)
    return redirect(url_for("login"))



@app.before_request
def require_login():
    allowed_route = ['login']
    if request.endpoint not in allowed_route and "name" not in session:
        return redirect('/login')



@app.route('//non_active_label//<name>//<document_id>/', methods=["POST", "GET"])
def non_active_label(name, document_id):
    st = time.time()
    get_document_information = url + "//get_document_information"
    response = requests.post(get_document_information, json={ "document_id": document_id,
                                                        "user_id":session["user_id"]
                                                         }).json()

    text = all_texts["text"][str(document_id)]
    words = get_words(response["topic"],  text)
    old_labels = list(set(predictions))
    labels = list(set(session["labels"].strip(",").split(",")))
    print(labels)

    if request.method =="POST":

        label = request.form.get("label")
        drop = request.form.get("suggestion")
        print(label)
        print(drop)

        # if label and drop:
        #     print("true")

        name=name 
        document_id=str(document_id)
        user_id = session["user_id"]
        et = time.time()
        response_time = et - st
        
        recommend_document = "https://nist-topic-model.umiacs.umd.edu/recommend_document"
        recommend_document = url + "//recommend_document"
        posts = requests.post(recommend_document, json={
        "user_id" : int(user_id),
        "label": label,
        "response_time": response_time,
        "document_id" : document_id
        }).json()

        next = posts["document_id"]
        predictions.append(label.lower())
        old_labels = list(set(predictions))
        
        session["labelled_document"] = session["labelled_document"]+","+str(document_id)
        docs = list(set(session["labelled_document"].strip(",").split(",")))
        session["labels"] = session["labels"] + "," + label
        labels = list(set(session["labels"].strip(",").split(",")))
        print(docs)
        print(session)
        save_labels(session)

        save_response(name, label, response_time, document_id, user_id)
        get_document_information = url + "//get_document_information"
        response = requests.post(get_document_information, json={ "document_id": posts["document_id"],
                                                        "user_id":session["user_id"]
                                                         }).json()
        # print(response["prediction"]) 
        return redirect(url_for("non_active_label", response=response, words=words, document_id=posts["document_id"], name=name, predictions=labels, pred=response["prediction"]))

    return render_template("nonactivelabel.html", response=response, words=words, document_id=document_id, text=text, name=name, predictions=labels, pred=response["prediction"])

  
@app.route("/try")
def trial():
    return render_template("try.html")
    

@app.route("/non_active/<name>/<topic_id>//<documents>")
def topic(name, topic_id, documents):
    print(topic_id)
    # res = get_single_document(documents, all_texts)
    # print(res)
    res = get_single_document(documents.strip("'[]'").split(", "), all_texts)


    return  render_template("topic.html", res = res, topic_id=topic_id)