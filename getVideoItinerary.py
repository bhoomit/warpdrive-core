# coding=utf-8
from flask import Flask, request, jsonify
import sys, json, requests, urllib, soundcloud, time, traceback, redis, subprocess, os, math
from threading import Thread
from random import randint
import youtube_upload as y_upload
from celery.task import task
from celery import Celery
import string
from urllib2 import quote

celery = Celery('getVideoItinerary', broker='redis://localhost/1')
root = "/home/bhoomit/data/"

# create client object with app credentials
scc = soundcloud.Client(client_id='xxxxxxxx')

r = redis.StrictRedis(host='localhost', port=6379, db=0)

app = Flask(__name__)

@app.route('/getItinerary', methods=['GET', 'POST'])
def getItinerary():
	try:
		itinerary = dict()
		print request.form.getlist('itineraryLoc[]')
		itinerary['data'] = request.form.getlist('itineraryLoc[]')
		itinerary['title'] = string.capwords(request.form.get('title').encode('utf-8'))
		itinerary['desc'] = request.form.get('desc').encode('utf-8')
		itinerary['url'] = request.form.get('url')
		itinerary['tags'] = request.form.get('tags')
		itinerary['ready_callback'] = request.form.get('ready_callback')
		itinerary['skipped'] = 0
 		requestId = int(time.time())
		r.set(requestId, json.dumps(itinerary))
		r.set('c_' + str(requestId), 0)

		arr= eval(itinerary['data'][0])
		latlng2 = arr[0] + ',' + arr[1]
		
		for arr in itinerary['data'][1:]:
			arr = eval(arr)
			latlng1 = latlng2
			latlng2 = arr[0] + ',' + arr[1]
			title = arr[2].encode('utf8')
			if r.exists('v_' + latlng1 + '::' + latlng2): continue
			r.rpush(latlng1 + '::' + latlng2, requestId)
			r.incr('c_' + str(requestId))
			callback = 'http://localhost:8089/dataReady/'
			print latlng1, latlng2, title
			requestPngs.delay(latlng1, latlng2, title, callback, requestId)
			#t = Thread(target = requestPngs, args=[atlng1, latlng2, title, callback, requestId])
			#t.start()
		if int(r.get('c_' + str(requestId))) <= 0: mergeVideo(str(requestId))
		# t = Thread(target = getNewSound)
		# t.start() 
	except:
		print traceback.format_exc()
		pass

	return jsonify({'status':'seccess','data': {'wd_video_id':requestId}})

def getNewSound():
	for filename in os.listdir(root):
		if filename.startswith("most_recent.mp3"):
			os.rename(root + filename, root + "old_most_recent.mp3")
	tracks = scc.get('/tracks', q='instrumental + symphony', license='cc-by-sa', duration={'from':60000,'to':600000})
	track = scc.get(tracks[randint(0,49)].stream_url, allow_redirects=False)
	urllib.urlretrieve(track.location, root + 'most_recent.mp3')
	return

@app.route('/getAtoB', methods=['GET', 'POST'])
def getAtoB():
	try:
		itinerary = dict()
		latlng1 = request.form.get('latlng1')
		latlng2 = request.form.get('latlng2')
		print latlng1
		arr = eval(latlng1)
		print arr
		latlng1 = arr[0] + ',' + arr[1]
		title1 = arr[2]
		arr = eval(latlng2)
		latlng2 = arr[0] + ',' + arr[1]
		title2 = arr[2]
		get1to2(latlng1, latlng2, title2)
		# get1to2(latlng2, latlng1, title1)
	except:
		print traceback.format_exc()
		pass

	return "success"

def get1to2(latlng1, latlng2, title):
	if r.exists('v_' + latlng1 + '::' + latlng2): return False
	callback = 'http://localhost:8089/dataReady/'
	print latlng1, latlng2, title
	requestPngs.delay(latlng1, latlng2, title, callback, 0)


@app.route('/dataReady/<ts>/<latlngstr>')
def dataReady(ts,latlngstr):	
	#cmd = "ffmpeg -y -r 13  -i " + root + "temp/%s/%s_%%03d.png -vb 30M -r 20 " % (ts,ts) + root + "temp/%s.mpeg" % (ts)
	cmd = "ffmpeg -y -r 13  -i " + root + "temp/%s/%s_%%03d.png -b 45M -an -r 20 " % (ts,ts) + root + "temp/%s.mpeg" % (ts)
	print cmd
	try:
		proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		stdout, stderr = proc.communicate()
		r.set('v_' + latlngstr,ts)
		print stdout
		print stderr
		t = Thread(target = onDataReady, args=[latlngstr])
		t.start()
	except:
		print traceback.format_exc()
		pass
	return "success"

def onDataReady(latlngstr):
	print "data ready for :: " + latlngstr
	len = r.llen(latlngstr)
	print str(len)
	for i in range(0,len):
		key = r.rpop(latlngstr) 
		r.decr('c_' + key)
		if int(r.get('c_' + key)) <= 0:
			mergeVideo(key)
	

@app.route('/mergeVideo/<rqId>')
def mergeVideo(rqId):
	print "merge video " + rqId
	itinerary = json.loads(r.get(rqId))
	skipped = 0
	arr= eval(itinerary['data'][0])
	latlng2 = arr[0] + ',' + arr[1]
	v_files = ''
	day = 0
	for arr in itinerary['data'][1:]:
		arr = eval(arr)
		latlng1 = latlng2
		latlng2 = arr[0] + ',' + arr[1]
		latlngstr = r.get('v_' + latlng1 + '::' + latlng2)
		if day != arr[3]:
			day = arr[3]
			v_files += '|' + root + 'days/day' + str(day) + '.mpeg'
		if latlngstr == '-1':
			skipped += 1
			continue;
		v_files += '|' + root + 'temp/' + latlngstr + '.mpeg'
	
	r.set(rqId, json.dumps(itinerary))	
	try:
		cmd = 'ffmpeg -y -i "concat:' + v_files[1:] + '" -codec copy -y ' + root + rqId + '_v.mpeg'
		print cmd
		proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		stdout, stderr = proc.communicate()
		print stdout
		print stderr

		a_files = getRandomMusic(getFileDuration(rqId + '_v.mpeg'))

		print 'ffmpeg -y -i ' + root + rqId + '_v.mpeg -i ' + a_files
		cmd = 'ffmpeg -y -i ' + root + rqId + '_v.mpeg -i "' + a_files + '" -map 0:0 -map 1:0 -acodec copy -vcodec copy -shortest -y ' + root + rqId + '.mpeg'
		print cmd
		proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		stdout, stderr = proc.communicate()
		print stdout
		print stderr

		t = Thread(target = youtube_upload, args=[root + rqId + '.mpeg', itinerary['title'], itinerary['tags'], itinerary['desc'], itinerary['ready_callback'], rqId])
		t.start()

	except:
		print traceback.format_exc()
		pass
	return "success"	

def getFileDuration(filepath):
	try:
		cmd = "ffprobe -loglevel error -show_streams " + root + filepath + " | grep duration= | cut -f2 -d="
		print cmd
		proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		stdout, stderr = proc.communicate()
		return float(stdout)
	except:
		print traceback.format_exc()
		pass
	return 0.0

def youtube_upload(path, title, tags, desc, ready_callback, ts):
	v_id = y_upload.py_upload(path, title.encode('utf-8'), tags.encode('utf-8'), desc.encode('utf-8'), "19", 'public')
	print v_id
	payload = {'video_id': ts, 'youtube_link': v_id}
	print payload
	requests.get(ready_callback, params=payload)


@task(ignore_result=True)
def requestPngs(latlng1, latlng2, title, callback, requestId):
	if r.exists('v_' + latlng1 + '::' + latlng2): return True
	payload = {'latlng1':latlng1,'latlng2':latlng2, 'title': title, 'callback':callback, 'requestId':requestId }
	requests.post("http://localhost:8088/",data=payload)
	return True

def getRandomMusic(len):
	num = randint(1,2)
	mPath = "music/" + str(num) + ".mp3"
	times = int(math.floor(len/getFileDuration(mPath)))
	mPath = root + mPath
	if times > 1:
		mPath = 'concat:' + mPath
		for m in range(1,times):
			mPath += '|' + mPath
	
	return mPath

@app.route('/phantomError', methods=['GET', 'POST'])
def phantomError():
	error = dict()
	error['message'] = request.args.get('message', '')
	error['latlng1'] = request.args.get('latlng1','')
	error['latlng2'] = request.args.get('latlng2', '')
	error['title'] = request.args.get('title','')
	r.sadd('error',json.dumps(error))
	latlngstr = error['latlng1'] + "::" + error['latlng2']
	r.set('v_' + latlngstr, "-1")
	t = Thread(target = onDataReady, args=[latlngstr])
	t.start()
	return "success"

if __name__ == '__main__':
    app.run(port="8089")



