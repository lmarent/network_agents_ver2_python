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

def isBlank (myString):
    if myString and myString.strip():
        #myString is not None AND myString is not empty or blank
        return False
    #myString is None OR myString is empty or blank
    return True

def getProfitTableData(periods, data):
    providerdata = data['Provider']
    providerVector = np.zeros(providerdata.size)
    for i in range(0,providerdata.size):
        providerVector[i] = float((providerdata[i])[-1:])
    tableData = [data['Period'], providerVector, data['Profits']]
    tableData = np.array(tableData)
    tableData = np.transpose(tableData)
    tableData = tableData[np.in1d(tableData[:,0], periods )]
    return tableData

def getProfitProviderData(profitdata, provider):
    return profitdata[np.in1d(profitdata[:,1], [float(provider)])]
    
def completeProfitInformation(periods, provider, providerData):
    vecReturn = np.zeros((len(periods),3))
    for period in periods:
        if ((providerData[:,0]).size > 1):
            if (period in providerData[:,0]):
                index = (providerData[:,0]).tolist().index(period)
                vecReturn[period - 1, 0] = providerData[index, 0]
                vecReturn[period - 1, 1] = providerData[index, 1]
                vecReturn[period - 1, 2] = providerData[index, 2]
            else:
                vecReturn[period - 1, 0] = period
                vecReturn[period - 1, 1] = provider
                vecReturn[period - 1, 2] = 0
        else:
            if (period == providerData[:,0]):
                vecReturn[period - 1, 0] = providerData[0, 0]
                vecReturn[period - 1, 1] = providerData[0, 1]
                vecReturn[period - 1, 2] = providerData[0, 2]
            else:
                vecReturn[period - 1, 0] = period
                vecReturn[period - 1, 1] = provider
                vecReturn[period - 1, 2] = 0
    return vecReturn

def getTableData(period, data):

    # Establish the size of points which are relative to the quantity sold.
    quantitydata = data['Quantity']
    maxQuantity = np.max(quantitydata)
    quantityVector = np.zeros(quantitydata.size)
    if (maxQuantity > 0):
        for i in range(0,quantitydata.size):
            quantityVector[i] = ((quantitydata[i] / maxQuantity) * 64 ) + 1
    else:
        for i in range(0,quantitydata.size):
            quantityVector[i] = 1

    providerdata = data['Provider']
    providerVector = np.zeros(providerdata.size)

    for i in range(0,providerdata.size):
        providerVector[i] = float((providerdata[i])[-1:])
    tableData = [data['Period'], data['Delay'], data['Price'], quantityVector, data['Color'], providerVector]
    tableData = np.array(tableData)
    tableData = np.transpose(tableData)
    tableData = tableData[np.in1d(tableData[:,0], [float(period)])]

    return tableData

def getProviderData(offerdata, provider):
    return offerdata[np.in1d(offerdata[:,5], [float(provider)])]

def generate_figure(directory, profit_evolution_file, offer_evolution_file):

    profit_evolution_file = directory + '/' + agent_properties.result_directory + profit_evolution_file
    dataProfit = np.genfromtxt(profit_evolution_file, delimiter=",", usecols=(0,1,2,3,4,5), 
                         dtype=[('Period', np.float64),('Provider',np.str_,16), ('Profits', np.float64) ])

    offer_evolution_file = directory + '/' + agent_properties.result_directory + offer_evolution_file
    data = np.genfromtxt(offer_evolution_file, delimiter=",", usecols=(0,1,2,3,4,5), 
                         dtype=[('Period', np.float64),('Delay',np.float64),('Price',np.float64),('Quantity',np.float64),('Color',np.float64),('Provider',np.str_,16) ])

    maxPeriod = np.max(data['Period'])
    minDelay = np.min(data['Delay'])
    maxDelay = np.max(data['Delay'])
    minPrice = np.min(data['Price'])
    maxPrice = np.max(data['Price'])

    colors = {1: 'b', 2: 'g', 3: 'r', 4: 'm', 5: 'orange', 6: 'c', 7: 'y', 8: 'greenyellow', 9: 'darkred', 10: 'crimson'}

    maxProfits = np.max(dataProfit['Profits'])
    minProfits = np.min(dataProfit['Profits'])
    vendors = np.unique(dataProfit['Provider'])
    numVendors = vendors.size
    periods =[]
    for period in range(0,int(maxPeriod)):

        print 'Period:'+ str(period)
        figure = plt.figure()
        figure.set_size_inches(5, 3.5)

        # Offers Evolution.
        ax1 = figure.add_subplot(1,2,1)
        tableData = getTableData(period + 1, data)
        numCentroids = 3
        offerdata = tableData[:,[1,2]]
        centroids,_ = kmeans(offerdata,numCentroids)
        idx,_ = vq(offerdata,centroids)
        ax1.set_xlabel("Delay (ms)", fontsize=8)
        ax1.set_xlim( minDelay, maxDelay )
        ax1.set_ylabel( "Price(Usd)", fontsize=8 )
        ax1.set_ylim( minPrice, maxPrice )
        providers = np.unique(tableData[:,5])
        rects = []
        labels = []
        for provider in providers:
            providerdata = getProviderData(tableData, provider)
            sc = ax1.scatter(providerdata[:,1],providerdata[:,2], marker = 'o', color = colors[int(provider)], s = providerdata[:,3], label = 'Provider '+ str(int(provider)))
            labels.append('Provider '+ str(int(provider)))
            rect = matplotlib.patches.Rectangle((0, 0), 1, 1, fc=colors[int(provider)])
            rects.append(rect)
        ax1.legend(tuple(rects), tuple(labels), loc='best', prop={'size':8})
        # ax1.plot(centroids[:,0],centroids[:,1],'sg',markersize=8)
        for tick in ax1.yaxis.get_major_ticks():
            tick.label.set_fontsize(8) 
        for tick in ax1.xaxis.get_major_ticks():
            tick.label.set_fontsize(8) 

        # Profits Figure

        ax2 = figure.add_subplot(1,2,2)
        periods.append(period + 1)
        tableProfitData = getProfitTableData(periods, dataProfit)
        width = 0.35
        ax2.set_xlabel("Periods", fontsize=8)
        ax2.set_xlim( 1, int(maxPeriod) )
        ax2.set_ylabel( "Profits(Usd)", fontsize=8 )
        #ax1.set_ylim( minProfits, maxProfits * numVendors)
        providers = np.unique(tableProfitData[:,1])
        firstTime = True
        groups = []
        labels = []
        for provider in providers:
            providerProfitdata = getProfitProviderData(tableProfitData, provider)
            providerProfitdata = completeProfitInformation(periods, provider, providerProfitdata)
            if firstTime == True:
                sc = ax2.bar(tuple(periods), tuple(providerProfitdata[:,2]), width, color=colors[int(provider)], edgecolor = "none")
                firstTime = False
            else:
                sc = ax2.bar(tuple(periods), tuple(providerProfitdata[:,2]), width, color=colors[int(provider)], bottom=lastdata, edgecolor = "none")
            lastdata = providerProfitdata[:,2]
            groups.append(sc[0])
            labels.append('Provider '+ str(int(provider)))
            print 'lastdata' + str(lastdata)
        ax2.legend(tuple(groups), tuple(labels), loc='best', prop={'size':8})
        for tick in ax2.yaxis.get_major_ticks():
            tick.label.set_fontsize(8) 
        for tick in ax2.xaxis.get_major_ticks():
            tick.label.set_fontsize(8) 

        output_file = directory + '/' + agent_properties.result_directory + 'images/integrated_plot_' + str(period+1) + '.eps'
        figure.tight_layout()
        plt.savefig(output_file)


def main(argv):
    profitfile = ''
    offerfile = ''
    directory = module_locator.module_path()
    try:
        opts, args = getopt.getopt(argv,"hp:o:",["pfile=","ofile="])
    except getopt.GetoptError:
        print 'offers_evolution.py -p <profitfile> -o <offerfile>'
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print 'offers_evolution.py -p <profitfile> -o <offerfile>'
            sys.exit()
        elif opt in ("-p", "--pfile"):
            profitfile = arg
        elif opt in ("-o", "--ofile"):
            offerfile = arg
    if ((isBlank(profitfile) == False) 
            and (isBlank(offerfile) == False)):
        generate_figure(directory, profitfile, offerfile)
    print 'Profit file is "', profitfile
    print 'Offer file is "', offerfile

if __name__ == "__main__":
   main(sys.argv[1:])
