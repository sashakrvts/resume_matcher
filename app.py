from flask import Flask, render_template, request, session, redirect, url_for
import pickle
from jdExtraction import jdExtraction
from resumeExtraction import ResumeExtraction
import requests
import os
from werkzeug.utils import secure_filename
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
import sys, fitz
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import CountVectorizer

def allowedExtension(filename):
    return '.' in filename and filename.rsplit('.',1)[1].lower() in ['docx','pdf']

jdextractorObj = pickle.load(open("jdExtraction.pkl","rb"))
resumeExtractionObj = pickle.load(open("resumeExtraction.pkl","rb"))
app = Flask(__name__)
UPLOAD_FOLDER = 'static/JD'
app.config['UPLOAD_FOLDER']=UPLOAD_FOLDER

app.secret_key = "Resume_screening"
app.config['MONGO_URI'] = "mongodb+srv://Cluster71733:Y0R5dU5aSXdT@cluster71733.vlqpcv9.mongodb.net/DiplomDatabase?retryWrites=true&w=majority"
mongo = PyMongo(app)
dbJD = mongo.db.JD
dbResume = mongo.db.dbResume


@app.route("/")
def index():
    return render_template("index.html")

@app.route("/uploadJD", methods=['POST'])
def uploadJD():
        file = request.files['jd']
        filename = secure_filename(file.filename)
        if file and allowedExtension(file.filename):
             file.save(os.path.join(app.config['UPLOAD_FOLDER'],filename))
             fetchedData=jdextractorObj.extractorData("static/JD/"+filename,file.filename.rsplit('.',1)[1].lower())
             result = None
             result1 = dbJD.insert_one({"Skills":list(fetchedData[0]),"Education":fetchedData[1],"JD_Data":fetchedData[2]}).inserted_id
             if result1 == None:
                return render_template("StartFind.html",successMsg="Problem in Data Storage")
             else:
                session['jd_id'] = str(result1)
                return render_template("StartFind.html",successMsg="Job Description Uploaded!!")
def matcher(job_desc,resume_text):
    text=[resume_text,job_desc]
    cv=CountVectorizer()
    count_matrix=cv.fit_transform(text)
    matchper=cosine_similarity(count_matrix)[0][1] * 100
    return round(matchper,3)

@app.route("/showCandidates")
def showCandidates():
    TopEmployeers=None
    TopEmployeers=None
    TopEmployeers=dbResume.find({"Total_Percentage":{"$gt":20},"JD_ID":{"$eq":session['jd_id']}},{"Name":1,"Mobile_no":1,"Email":1,"Skills":1,"Skills_percentage":1,"Education":1,"Total_Percentage":1}).sort([("Total_Percentage",-1)])
    if TopEmployeers == None:
        return render_template("Show_top_matching.html",successMsg="No Candidate found")
    else:
        selectedResumes={}
        cnt = 0
        for i in TopEmployeers:
            selectedResumes[cnt] = {"Name":i['Name'],"Email":i['Email'],"Mobile_no":i['Mobile_no'],"Skills":i['Skills'],"Skills_percentage":i['Skills_percentage'],"Education":i['Education'],"Total_Percentage":i['Total_Percentage']}
            cnt += 1
        return render_template("Show_top_matching.html",len = len(selectedResumes), data = selectedResumes,successMsg="Shortlisted Candidates")

@app.route("/scanResume")
def scanResume():
    se=dbJD.find_one({"_id":ObjectId(session['jd_id'])},{"Skills":1,"Education":1,"JD_Data":1})
    entries = os.listdir('Resumes/')
    for entry in entries:
        try:
            data = resumeExtractionObj.extractorData('Resumes/'+entry,"pdf")
            da = round((len(list(set(se['Skills']).intersection(data[3])))/len(list(se['Skills'])))*100,3)
            skills_percentage = round((da * 60 / 100),3)
            resume_percentage = matcher(se['JD_Data'],data[5])
            total = round((skills_percentage + (resume_percentage * 40) / 100),3)
            result = None
            result = dbResume.insert_one({"Name":data[0],"Mobile_no":data[1],"Email":data[2],"Skills":list(data[3]),"Skills_percentage":da,"Education":data[4],"JD_Percentage":resume_percentage,"Total_Percentage":total,"JD_ID":session['jd_id']}).inserted_id
        except:
            continue
    return redirect(url_for("showCandidates"))

if __name__=="__main__":
    app.run(debug=True)