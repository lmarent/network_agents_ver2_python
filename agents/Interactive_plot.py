import matplotlib.pyplot as plt
import matplotlib.animation as animation
import time

fig = plt.figure()
ax1 = fig.add_subplot(1,1,1)

def animate(i):
	ax1.clear()
	pullData = open('Offers_evolution.txt','r').read()
	print "plotting for interval: " + str(i) 
	dataArray = pullData.split('\n')
	# The first line brings the titles of the axis and valid interval
	if len(dataArray) > 0:
		header = dataArray.pop(0) 
		headerValues = header.split(',')		
	xar = []
	yar = []
	colorar = []
	quantityar = []
	for eachLine in dataArray:
		if len(eachLine)>1:
			x,y, quantity, color = eachLine.split(',')
			xar.append(float(x))
			yar.append(float(y))
			colorar.append(float(color))
			quantityar.append(quantity)
	
	# Establish the titles and range of variables for the axis.
	print 'Number of fields in header values is:' + str(len(headerValues))
	if (len(headerValues) == 6):
		ax1.set_xlabel(headerValues[0])
		excess = (float(headerValues[2]) - float(headerValues[1])) * 0.1
		minx = float(headerValues[1]) - excess
		maxx = float(headerValues[2]) + excess
		ax1.set_xlim( minx, maxx )
		ax1.set_ylabel(headerValues[3])
		excess = (float(headerValues[5]) - float(headerValues[4])) * 0.1
		miny = float(headerValues[4]) - excess
		maxy = float(headerValues[5]) + excess
		ax1.set_ylim( miny, maxy )
	ax1.scatter(
	    xar, yar, marker = 'o', c = colorar, s = 30,
	    cmap = plt.get_cmap('Spectral'))
	
	# defines the labels for every point created.
	for label, x, y in zip(quantityar, xar, yar):
	    plt.annotate(
	    label, 
	    xy = (x, y), xytext = (-10, 10),
	    textcoords = 'offset points', ha = 'right', va = 'bottom',
	    bbox = dict(boxstyle = 'round,pad=0.2', fc = 'yellow', alpha = 0.5),
	    arrowprops = dict(arrowstyle = '->', connectionstyle = 'arc3,rad=0'))


ani = animation.FuncAnimation(fig,animate,interval=1000)
plt.show()



