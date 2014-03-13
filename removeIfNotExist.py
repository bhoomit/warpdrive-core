import os, redis

root = '/home/bhoomit/data/'
r = redis.StrictRedis(host='localhost', port=6379, db=0)

keys = r.keys("v_*")
print "Total Keys :: " + str(len(keys))
removed = 0
for key in keys: 
	if not os.path.exists(root + 'temp/' + r.get(key) + '.mpeg'):
		r.delete(key)
		print "Removed key :: " + key
		removed += 1
	else:
		print "Not removed key :: " + key
	

print "Total keys removed :: " + str(removed)
