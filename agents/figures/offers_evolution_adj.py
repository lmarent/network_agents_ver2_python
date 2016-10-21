
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

def generate_figure(directory, input_file, output_file):
    input_file = directory + '/' + agent_properties.result_directory + input_file
    data = np.genfromtxt(input_file, skip_header=1, delimiter=",", usecols=(0,1,2,3,4,5,6,7), 
                             dtype=[('Period', np.float64),('Delay',np.float64),
                                    ('Price',np.float64),('Quantity',np.float64),
                                    ('Color',np.float64),('Provider',np.str_,16) ,
                                    ('BidId',np.str_,36),('ParentBidId',np.str_,36) ,
                                    ])

    i = 0
    bids = {} # This contains the bidId being ancestors of the rest of bids and their children bids.
    ancestors = {}
    bidData = {}
    bidByPeriod = {}
    while i < len(data):
        parentBidId = (data[i])['ParentBidId']
        bidId = (data[i])['BidId']
        bidData[bidId] = {'Period' : (data[i])['Period'], 'Delay' : (data[i])['Delay'], 'Price' : (data[i])['Price'] }
        period = (data[i])['Period']
        if len(parentBidId) == 0:
            bids[bidId] = []
            ancestors[bidId] = bidId
            (bids[bidId]).append(bidId)
        else:
            ancestors[bidId] = ancestors[parentBidId]
            ancestorBid = ancestors[parentBidId]
            (bids[ancestorBid]).append(bidId)
        if period not in bidByPeriod:
            bidByPeriod[period] = []
        (bidByPeriod[period]).append(bidId)
        i = i + 1

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

    ax1.set_xlim( 0, maxPeriod )
    ax1.set_ylim( minPrice, maxPrice )
    ax1.set_ylabel( "Price", fontsize=8 )
    ax1.set_xlabel("Periods", fontsize=8)

    ax2 = figure.add_subplot(1,2,2)
    ax2.set_xlim( 0, maxPeriod )
    ax2.set_ylim( minDelay, maxDelay )
    ax2.set_ylabel( "Delay", fontsize=8 )
    ax2.set_xlabel("Periods", fontsize=8)
    
    xdata = []
    delaydata = {}
    pricedata = {}
    for period in range(1,int(maxPeriod+1)):
        xdata.append(period)
    for bidId in bids:
        list_bid = bids[bidId]
        delaydetaildata = []
        pricedetaildata = []
        for period in range(1,int(maxPeriod+1)):
            delaydetaildata.append(np.nan)
            pricedetaildata.append(np.nan)
        if len(list_bid) > 1:
            for bidIdTmp in list_bid:
                period = int(np.asscalar((bidData[bidIdTmp])['Period']))
                delay = (bidData[bidIdTmp])['Delay']
                price = (bidData[bidIdTmp])['Price']
                delaydetaildata[period- 1] = delay
                pricedetaildata[period- 1] = price
            delaydata[bidId] = delaydetaildata
            pricedata[bidId] = pricedetaildata
    
    for bidId in pricedata:
        ax1.plot(xdata, pricedata[bidId]) 
        
    for bidId in delaydata:
        ax2.plot(xdata, delaydata[bidId])  

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