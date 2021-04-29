#!/usr/bin/env python3

from flask import Flask, render_template, request, redirect, url_for, make_response
from markupsafe import escape
import pymongo
import datetime
from bson.objectid import ObjectId
import os
import subprocess

# instantiate the app
app = Flask(__name__)
app.config["MONGO_URI"] = 'mongodb://pa1363:fGZjN5Ae@class-mongodb.cims.nyu.edu:27107/pa1363'

# load credentials and configuration options from .env file
# if you do not yet have a file named .env, make one based on the template in env.example
import credentials
config = credentials.get()

# turn on debugging if in development mode
if config['FLASK_ENV'] == 'development':
    # turn on debugging, if in development
    app.debug = True # debug mnode

# make one persistent connection to the database
connection = pymongo.MongoClient(config['MONGO_HOST'], 27017, 
                                username=config['MONGO_USER'],
                                password=config['MONGO_PASSWORD'],
                                authSource=config['MONGO_DBNAME'])


db = connection[config['MONGO_DBNAME']] # store a reference to the database

# set up the routes

@app.route('/')
def home():
    """
    Route for the home page
    """
    return render_template('index.html')


@app.route('/read')
def read():
    """
    Route for GET requests to the read page.
    Displays some information for the user with links to other pages.
    """
    docs = db.profs.distinct("prof_name") 
    return render_template('read.html', docs=docs) # render the read template

@app.route('/file/<filename>')
def file(filename):
    return mongo.send_file(filename)


@app.route('/create')
def create():
    """
    Route for GET requests to the create page.
    Displays a form users can fill out to create a new document.
    """
    return render_template('create.html') # render the create template


@app.route('/create', methods=['POST'])
def create_post():
    """
    Route for POST requests to the create page.
    Accepts the form submission data for a new document and saves the document to the database.
    """
    
    prof_name = request.form["prof_name"]
    course_name = request.form["course_name"]
    course_rating = request.form["course_rating"]
    text_review = request.form["text_review"]
    prof_rating = request.form["prof_rating"]
    
    # create a new document with the data the user entered
    doc = {
        "prof_name": prof_name,
        "course_name": course_name,
        "course_rating":course_rating,
        "text_review":text_review,
        "prof_rating":prof_rating,
        "created_at": datetime.datetime.utcnow(),
    }
    db.profs.insert_one(doc) # insert a new document

    return redirect(url_for('read')) # tell the browser to make a request for the /read route


@app.route('/view_prof/<prof_name>')
def view_prof(prof_name):
    """
    Route for VIEW 
    Displays review information about the Professor that has been clicked.
    """
    docs = db.profs.find({"prof_name":prof_name}).sort("created_at",-1)
    avg_prof_ratings_docs = db.profs.find({"prof_name":prof_name},{"_id":-1, "prof_rating":1})
    prof_rating_list = []
    for i in avg_prof_ratings_docs: 
        prof_rating_list.append(int(i["prof_rating"]))
    avg_prof_rating = sum(prof_rating_list)/len(prof_rating_list)
    avg_prof_rating = round(avg_prof_rating,2)

    avg_class_ratings_docs = db.profs.find({"prof_name":prof_name},{"_id":-1, "course_rating":1})
    class_rating_list = []
    for i in avg_class_ratings_docs: 
        class_rating_list.append(int(i["course_rating"]))
    avg_course_rating = sum(class_rating_list)/len(class_rating_list)
    avg_course_rating = round(avg_course_rating,2)

    if avg_prof_rating<=2.5: 
        color_1 = "red"
    
    elif avg_prof_rating<=3.75:
        color_1 = "orange"

    else:
        color_1 = "green"

    if avg_course_rating<=2.5: 
        color_2 = "green"
    
    elif avg_course_rating<=3.75:
        color_2 = "orange"

    else:
        color_2 = "red"

        
    return render_template('view.html', prof_name = prof_name, docs = docs, avg_prof_rating = avg_prof_rating, avg_course_rating = avg_course_rating, color_prof = color_1, color_class = color_2) # render the read template

@app.route('/edit/<mongoid>')
def edit(mongoid):
    """
    Route for GET requests to the edit page.
    Displays a form users can fill out to edit an existing record.
    """
    doc = db.profs.find_one({"_id": ObjectId(mongoid)})
    return render_template('edit.html', mongoid=mongoid, doc=doc) # render the edit template


@app.route('/edit/<mongoid>', methods=['POST'])
def edit_post(mongoid):
    """
    Route for POST requests to the edit page.
    Accepts the form submission data for the specified document and updates the document in the database.
    """
    prof_name = request.form["prof_name"]
    course_name = request.form["course_name"]
    course_rating = request.form["course_rating"]
    text_review = request.form["text_review"]
    prof_rating = request.form["prof_rating"]

    doc = {
        # "_id": ObjectId(mongoid),
        "prof_name": prof_name,
        "course_name": course_name,
        "course_rating":course_rating,
        "text_review":text_review,
        "prof_rating":prof_rating,
        "created_at": datetime.datetime.utcnow(),
    }

    db.profs.update_one(
        {"_id": ObjectId(mongoid)}, # match criteria
        { "$set": doc }
    )

    return redirect(url_for('read')) # tell the browser to make a request for the /read route


@app.route('/delete/<mongoid>')
def delete(mongoid):
    """
    Route for GET requests to the delete page.
    Deletes the specified record from the database, and then redirects the browser to the read page.
    """
    db.profs.delete_one({"_id": ObjectId(mongoid)})
    return redirect(url_for('read')) # tell the web browser to make a request for the /read route.

@app.route('/webhook', methods=['POST'])
def webhook():
    """
    GitHub can be configured such that each time a push is made to a repository, GitHub will make a request to a particular web URL... this is called a webhook.
    This function is set up such that if the /webhook route is requested, Python will execute a git pull command from the command line to update this app's codebase.
    You will need to configure your own repository to have a webhook that requests this route in GitHub's settings.
    Note that this webhook does do any verification that the request is coming from GitHub... this should be added in a production environment.
    """
    # run a git pull command
    process = subprocess.Popen(["git", "pull"], stdout=subprocess.PIPE)
    pull_output = process.communicate()[0]
    # pull_output = str(pull_output).strip() # remove whitespace
    process = subprocess.Popen(["chmod", "a+x", "flask.cgi"], stdout=subprocess.PIPE)
    chmod_output = process.communicate()[0]
    # send a success response
    response = make_response('output: {}'.format(pull_output), 200)
    response.mimetype = "text/plain"
    return response

@app.errorhandler(Exception)
def handle_error(e):
    """
    Output any errors - good for debugging.
    """
    return render_template('error.html', error=e) # render the edit template


if __name__ == "__main__":
    #import logging
    #logging.basicConfig(filename='/home/ak8257/error.log',level=logging.DEBUG)
    app.run(debug = True)
