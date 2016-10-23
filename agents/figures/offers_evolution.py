
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from numpy import vstack,array
from numpy.random import rand
from scipy.cluster.vq import kmeans,vq
import sys, getopt
import os,inspect
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir) 
sys.path.insert(1,parentdir + '/foundation') 

import module_locator
import agent_properties



DELIMITER = ','

def isBlank (myString):
    if myString and myString.strip():
        #myString is not None AND myString is not empty or blank
        return False
    #myString is None OR myString is empty or blank
    return True

def getProviderData(offerdata, provider):
    return offerdata[np.in1d(offerdata[:,5], [provider])]

def getPeriodProviderData(offerdata, period, provider):
    print period 
    periodData = offerdata[np.in1d(offerdata[:,0], [period])]
    if (periodData.size > 0):
        periodProviderData = periodData[np.in1d(periodData[:,5], [provider])]
        if (periodProviderData.size > 0):
            return periodProviderData
        else:
            return None
    else:
        return None

def getPeriodProviderOffers(tableData, period, provider):
    ''' Returns a list with the data for the given provider and period, 
    the list can be divided by six elements.
    '''
    periodData = tableData[np.in1d(tableData[:,0], [period])]
    if (periodData.size > 0):
        periodProviderData = periodData[np.in1d(periodData[:,5], [provider])]
        if (len(periodProviderData) > 0):
            minPrice = np.min(periodProviderData[:,2])
            minPriceData = periodProviderData[np.in1d(periodProviderData[:,2], [minPrice])]
            if (minPriceData.shape != (1,6)):
                minPriceData.reshape(minPriceData.size)
            maxPrice = np.max(periodProviderData[:,2])
            maxPriceData = periodProviderData[np.in1d(periodProviderData[:,2], [maxPrice])]
            if (maxPriceData.shape != (1,6)):
                maxPriceData.reshape(maxPriceData.size) 
            data_return = np.concatenate((minPriceData, maxPriceData),axis=0)
            return data_return
        else:
            return None
    else:
        return None

def getTableData(data):
    providerdata = data['Provider']
    providerVector = np.zeros(providerdata.size)
    for i in range(0,providerdata.size):
        providerVector[i] = float((providerdata[i])[-1:])
    tableData = [data['Period'], data['Delay'], data['Price'], data['Quantity'], data['Color'], providerVector]
    tableData = np.array(tableData)
    tableData = np.transpose(tableData)
    return tableData

def eliminateLinesNotPurchased(tableData, maxPeriod, vendors):
    ''' 
    If the provider does not have offers purchase in one period, the 
    software let the offers with the maximum and minimum prices.
    '''
    # First put on the graph purchased offers.
    i = 0
    firstTime = True
    while (i < len(tableData)):
        if (tableData[i,3] > 0 ):
            line = tableData[i,:]
            if firstTime == True:
                vec_return = line
                firstTime = False
            else:
                vec_return = np.concatenate((vec_return, 
                                            tableData[i,:]), axis=0)
        i = i + 1	
    purchasedOffers = np.reshape(vec_return, (vec_return.size / 6, 6))

    # Cover periods asking if there is at least one offer with quantity. If it is not 
    # the case, it appends the offer with the minimum price and the one with the maximum 
    # price.
    #firstTime = True
    #for period in range(1,int(maxPeriod + 1)):
#	for vendor in vendors:
#	    periodProviderData = getPeriodProviderData(purchasedOffers, period, vendor)
#	    if periodProviderData is None:
#		periodProviderDataOffers = getPeriodProviderOffers(tableData, period, vendor)
#		if (periodProviderDataOffers != None):
#		    if firstTime == True:
#			vec_return2 = periodProviderDataOffers
#			firstTime = False
#		    else:
#			vec_return2 = np.concatenate((vec_return2, 
#					    periodProviderDataOffers), axis=0)
#	    else:
#		pass 
#    purchasedOffers.reshape((purchasedOffers.size))
#    finalData = np.concatenate((purchasedOffers, 
#					    vec_return2), axis=0)
#    finalData = np.reshape(finalData, (finalData.size / 6, 6))
#    print finalData
    return purchasedOffers

def generate_figure(directory, input_file, output_file):

    input_file = directory + '/' + agent_properties.result_directory + input_file
    print input_file
    data = np.genfromtxt(input_file, skip_header=1, delimiter=",", usecols=(0,1,2,3,4,5), 
                         dtype=[('Period', np.float64),('Delay',np.float64),
                                ('Price',np.float64),('Quantity',np.float64),
                                ('Color',np.float64),('Provider',np.str_,16) 
                                ])

    maxPeriod = np.max(data['Period'])
    minDelay = np.min(data['Delay'])
    maxDelay = np.max(data['Delay']) 
    minDelay = minDelay - ((maxDelay - minDelay) / 10)
    maxDelay = maxDelay + ((maxDelay - minDelay) / 10)

    minPrice = np.min(data['Price'])
    maxPrice = np.max(data['Price'])
    minPrice = minPrice - ((maxPrice - minPrice) / 10) 
    maxPrice = maxPrice + ((maxPrice - minPrice) / 10)    
    
    figure = plt.figure()
    figure.set_size_inches(6, 3)
    ax1 = figure.add_subplot(1,2,1)

    colors = {0: 'b', 1: 'g', 2: 'r', 3: 'm', 4: 'orange', 5: 'c', 6: 'y', 7: 'skyblue', 8: 'indigo', 9: 'yellowgreen'}
    markers = {0: 'o', 1: '+', 2: 'D', 3: 'x', 4: '1', 5: '2', 6: '4', 7: '8', 8: 'H', 9: '*'}

    tableData = getTableData(data)
    providers = np.unique(tableData[:,5])
    finalData = eliminateLinesNotPurchased(tableData, maxPeriod, providers)
    labels = []
    rects = []
    for provider in providers:
        print 'Provider:',  provider 
        
    for provider in providers:
        labels.append('Provider '+ str(int(provider)))
        firstTime = True    
        for period in range(1,int(maxPeriod+1)):
            purch = getPeriodProviderData(finalData, period, provider)
            if (purch is None): 
                pass
            else:
                sc = ax1.scatter(purch[:,0],purch[:,2], marker = markers[int(provider)], s= 10,  color = colors[int(provider)], label = 'Provider '+ str(int(provider)))
                if (firstTime == True):
                    rects.append(sc)
                    firstTime = False

    ax1.set_xlim( 0, maxPeriod )
#    ax1.set_ylim( minPrice, maxPrice )
    ax1.set_ylim( 0, 1.5 )
    ax1.set_ylabel( "Price", fontsize=8 )
    ax1.set_xlabel("Time", fontsize=8)
    ax1.legend(tuple(rects), tuple(labels), loc='best', prop={'size':8})
    for tick in ax1.yaxis.get_major_ticks():
        tick.label.set_fontsize(8) 
    for tick in ax1.xaxis.get_major_ticks():
        tick.label.set_fontsize(8) 

    ax2 = figure.add_subplot(1,2,2)
    labels = []
    rects = []
    for provider in providers:
        labels.append('Provider '+ str(int(provider)))
        #rect = matplotlib.patches.Rectangle((0, 0), 1, 1, fc=colors[int(provider)])
        #rects.append(rect)
        firstTime = True
        for period in range(1,int(maxPeriod+1)):
            purch = getPeriodProviderData(finalData, period, provider)
            if (purch is None): 
                pass
            else:
                sc2 = ax2.scatter(purch[:,0],purch[:,1], marker = markers[int(provider)], s= 10,  color = colors[int(provider)], label = 'Provider '+ str(int(provider)))
                if (firstTime == True):
                    rects.append(sc2)
                    firstTime = False
    ax2.set_xlim( 0, maxPeriod )
#    ax2.set_ylim( minDelay, maxDelay )
    ax2.set_ylim( 0, 1.5 )
    ax2.set_ylabel( "Quality", fontsize=8 )
    ax2.set_xlabel("Time", fontsize=8)
    ax2.legend(tuple(rects), tuple(labels), loc='best', prop={'size':8})
    for tick in ax2.yaxis.get_major_ticks():
        tick.label.set_fontsize(8) 
    for tick in ax2.xaxis.get_major_ticks():
        tick.label.set_fontsize(8) 

    figure.tight_layout(pad=0.4, w_pad=0.5, h_pad=1.0)
    output_file = directory + '/' + agent_properties.result_directory + 'images/' + output_file
    plt.savefig(output_file)


def main(argv):
    inputfile = ''
    outputfile = ''
    directory = module_locator.module_path()
    try:
        opts, args = getopt.getopt(argv,"hi:o:",["ifile=","ofile="])
    except getopt.GetoptError:
        print 'offers_evolution.py -i <inputfile> -o <outputfile>'
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print 'offers_evolution.py -i <inputfile> -o <outputfile>'
            sys.exit()
        elif opt in ("-i", "--ifile"):
            inputfile = arg
        elif opt in ("-o", "--ofile"):
            outputfile = arg
    if ((isBlank(inputfile) == False) 
            and (isBlank(outputfile) == False)):
        generate_figure(directory, inputfile, outputfile)
    print 'Input file is "', inputfile
    print 'Output file is "', outputfile

if __name__ == "__main__":
   main(sys.argv[1:])


