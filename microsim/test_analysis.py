# -*- coding: utf-8 -*-
"""
Created on Tue May 19 12:01:02 2020

@author: Natalie
"""


# test version, needs adapting to work across platform

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.pylab as pylab
import seaborn as sns
import geopandas as gpd
import os
import pickle
import imageio
from shapely.geometry import Point
import numpy as np
from scipy import ndimage
import pickle


# Read in data
# ------------

# To fix file path issues, use absolute/full path at all times
# Pick either: get working directory (if user starts this script in place, or set working directory
# Option A: copy current working directory:
base_dir = os.getcwd()  # get current directory (assume RAMP-UA)
data_dir = os.path.join(base_dir, "data") # go to output dir
# Option B: specific directory
#data_dir = 'C:\\Users\\Toshiba\\git_repos\\RAMP-UA\\dummy_data'

# read in details about venues
data_file = os.path.join(data_dir, "devon-schools","exeter schools.csv")
schools = pd.read_csv(data_file)
data_file = os.path.join(data_dir, "devon-retail","devon smkt.csv")
retail = pd.read_csv(data_file)

# read in pickle files
data_file = os.path.join(data_dir, "output","Individuals.pickle")
pickle_in = open(data_file,"rb")
individuals = pickle.load(pickle_in)
pickle_in.close()

data_file = os.path.join(data_dir, "output","PrimarySchool.pickle")
pickle_in = open(data_file,"rb")
primaryschool_dangers = pickle.load(pickle_in)
pickle_in.close()

data_file = os.path.join(data_dir, "output","SecondarySchool.pickle")
pickle_in = open(data_file,"rb")
secondaryschool_dangers = pickle.load(pickle_in)
pickle_in.close()

data_file = os.path.join(data_dir, "output","Retail.pickle")
pickle_in = open(data_file,"rb")
retail_dangers = pickle.load(pickle_in)
pickle_in.close()

data_file = os.path.join(data_dir, "output","Work.pickle")
pickle_in = open(data_file,"rb")
work_dangers = pickle.load(pickle_in)
pickle_in.close()

data_file = os.path.join(data_dir, "output","Home.pickle")
pickle_in = open(data_file,"rb")
home_dangers = pickle.load(pickle_in)
pickle_in.close()






# Preprocess data
# ---------------

# how many days have we got
nr_days = retail_dangers.shape[1] - 1
days = [i for i in range(0,nr_days)]

# total cases (SEIR) per area across time, and summed across MSOAs

# initialise variables
nrs_S = [0 for i in range(nr_days)] 
nrs_E = [0 for i in range(nr_days)] 
nrs_I = [0 for i in range(nr_days)] 
nrs_R = [0 for i in range(nr_days)] 
msoas = sorted(individuals.area.unique())
msoa_counts_S = pd.DataFrame(index=msoas)
msoa_counts_E = pd.DataFrame(index=msoas)
msoa_counts_I = pd.DataFrame(index=msoas)
msoa_counts_R = pd.DataFrame(index=msoas)

# loop aroud days
for d in range(0, nr_days):
    nrs = individuals.iloc[:,-nr_days+d].value_counts() 
    nrs_S[d] = nrs.get(0)  # susceptible?
    nrs_E[d] = nrs.get(1)  # exposed?
    nrs_I[d] = nrs.get(2)  # infectious?
    nrs_R[d] = nrs.get(3)  # recovered/removed?
    # S
    msoa_count_temp = individuals[individuals.iloc[:, -nr_days+d] == 0].groupby(['Area']).agg({individuals.columns[-nr_days+d]: ['count']})  
    msoa_counts_S = pd.merge(msoa_counts_S,msoa_count_temp,left_index = True, right_index=True)
    msoa_counts_S.rename(columns={ msoa_counts_S.columns[d]: 'Day'+str(d) }, inplace = True)
    # E
    msoa_count_temp = individuals[individuals.iloc[:, 73+d] == 1].groupby(['Area']).agg({individuals.columns[73+d]: ['count']})  
    msoa_counts_E = pd.merge(msoa_counts_E,msoa_count_temp,left_index = True, right_index=True)
    msoa_counts_E.rename(columns={ msoa_counts_E.columns[d]: 'Day'+str(d) }, inplace = True)
    # I
    msoa_count_temp = individuals[individuals.iloc[:, 73+d] == 2].groupby(['Area']).agg({individuals.columns[73+d]: ['count']})  
    msoa_counts_I = pd.merge(msoa_counts_I,msoa_count_temp,left_index = True, right_index=True)
    msoa_counts_I.rename(columns={ msoa_counts_I.columns[d]: 'Day'+str(d) }, inplace = True)
    # R
    msoa_count_temp = individuals[individuals.iloc[:, 73+d] == 3].groupby(['Area']).agg({individuals.columns[73+d]: ['count']})  
    msoa_counts_R = pd.merge(msoa_counts_R,msoa_count_temp,left_index = True, right_index=True)
    msoa_counts_R.rename(columns={ msoa_counts_R.columns[d]: 'Day'+str(d) }, inplace = True)
    
    # # sanity check: sum across MSOAs should be same as nrs_*
    # assert (msoa_counts_S.iloc[:,d].sum() == nrs_S[d])
    # assert (msoa_counts_E.iloc[:,d].sum() == nrs_E[d])
    # assert (msoa_counts_I.iloc[:,d].sum() == nrs_I[d])
    # assert (msoa_counts_R.iloc[:,d].sum() == nrs_R[d])




# !!! TEMPORARY - DELETE ONCE MICROSIM FIXED
# for now, original script not fully working (everyone is S so randomly make up some nrs and overwrite previous variables)
import random
random.seed()
for d in range(0, nr_days):
    for m in range(0,len(msoas)):
        total_msoa = msoa_counts_S.iloc[m,d]
        msoa_counts_E.iloc[m,d] = random.randrange(int(0.15*total_msoa), int(0.25*total_msoa), 1)
        msoa_counts_I.iloc[m,d] = random.randrange(int(0.1*total_msoa), int(0.2*total_msoa), 1)
        msoa_counts_R.iloc[m,d] = random.randrange(int(0.05*total_msoa), int(0.1*total_msoa), 1)
        msoa_counts_S.iloc[m,d] = total_msoa - msoa_counts_E.iloc[m,d] - msoa_counts_I.iloc[m,d] - msoa_counts_R.iloc[m,d]
        #assert (msoa_counts_S.iloc[m,d] + msoa_counts_E.iloc[m,d] + msoa_counts_I.iloc[m,d] + msoa_counts_R.iloc[m,d] == total_msoa)
    total_day = nrs_S[d]
    nrs_E[d] = msoa_counts_E.iloc[:,d].sum()
    nrs_I[d] = msoa_counts_I.iloc[:,d].sum()
    nrs_R[d] = msoa_counts_R.iloc[:,d].sum()
    nrs_S[d] = msoa_counts_S.iloc[:,d].sum()
    assert(total_day == nrs_S[d] + nrs_E[d] + nrs_I[d] + nrs_R[d])
    


# create (if first run, takes a while) or read in existing
# create
for d in range(0, nr_days):
    print(d)
    for v in range(0, len(home_dangers)):
        if d == 0:
            # set seed
            home_dangers.iloc[v,d+1] = 0
        else:
            home_dangers.iloc[v,d+1] = home_dangers.iloc[v,d] + random.randrange(-5, 5, 1)
            if home_dangers.iloc[v,d+1] < 0:
                home_dangers.iloc[v,d+1] = 0
data_file = os.path.join(data_dir, "output","Fake_home_dangers.pickle")
pickle_out = open(data_file,"wb")
pickle.dump(home_dangers, pickle_out)
pickle_out.close() 
# read
data_file = os.path.join(data_dir, "output","Fake_home_dangers.pickle")
pickle_in = open(data_file,"rb")
home_dangers = pickle.load(pickle_in)
pickle_in.close()
        
for d in range(0, nr_days):
    print(d)
    for v in range(0, len(work_dangers)):
        if d == 0:
            # set seed
            work_dangers.iloc[v,d+1] = 0
        else:
            work_dangers.iloc[v,d+1] = work_dangers.iloc[v,d] + random.randrange(-5, 5, 1)
            if work_dangers.iloc[v,d+1] < 0:
                work_dangers.iloc[v,d+1] = 0
    
    for v in range(0, len(primaryschool_dangers)):
        if d == 0:
            # set seed
            primaryschool_dangers.iloc[v,d+1] = 0
            secondaryschool_dangers.iloc[v,d+1] = 0
        else:
            primaryschool_dangers.iloc[v,d+1] = primaryschool_dangers.iloc[v,d] + random.randrange(-5, 5, 1)
            if primaryschool_dangers.iloc[v,d+1] < 0:
                primaryschool_dangers.iloc[v,d+1] = 0
            secondaryschool_dangers.iloc[v,d+1] = secondaryschool_dangers.iloc[v,d] + random.randrange(-5, 5, 1)
            if secondaryschool_dangers.iloc[v,d+1] < 0:
                secondaryschool_dangers.iloc[v,d+1] = 0
        
    for v in range(0, len(retail_dangers)):
        if d == 0:
            # set seed
            retail_dangers.iloc[v,d+1] = 0
        else:
            retail_dangers.iloc[v,d+1] = retail_dangers.iloc[v,d] + random.randrange(-5, 5, 1)
            if retail_dangers.iloc[v,d+1] < 0:
                retail_dangers.iloc[v,d+1] = 0
        
pickle_out = open(os.path.join(output_dir, "Individuals.pickle"),"wb")
pickle.dump(individuals_to_pickle, pickle_out)
pickle_out.close()        



   

    


# Add additional info about schools and retail including spatial coordinates
# merge
primaryschools = pd.merge(schools, primaryschool_dangers, left_index=True, right_index=True)
secondaryschools = pd.merge(schools, secondaryschool_dangers, left_index=True, right_index=True)
retail = pd.merge(retail, retail_dangers, left_index=True, right_index=True)


# Plot data
# ----------
msoas_nr = [i for i in range(0,len(msoas))]

# line plot SEIR: total E,I,R across time (summed over all areas)
fig, ax = plt.subplots()  # Create a figure and an axes.
ax.plot(days, nrs_E, label='Exposed')  # Plot some data on the axes.
ax.plot(days, nrs_I, label='Infectious')  # Plot more data on the axes...
ax.plot(days, nrs_R, label='Recovered')  # ... and some more.
ax.set_xlabel('Days')  # Add an x-label to the axes.
ax.set_ylabel('Number of people')  # Add a y-label to the axes.
ax.set_title("Infections over time")  # Add a title to the axes.
ax.legend()  # Add a legend.   

# Line plot of SEIR per MSOA at a given day
# ask user to pick a day
day2plot = int(input("Please type the number of the day you want to plot (0 to "+str(nr_days-1)+"): "))
fig, ax = plt.subplots()  # Create a figure and an axes.
ax.plot(msoas_nr, msoa_counts_E.iloc[:,day2plot].tolist(), label='Exposed')  
ax.plot(msoas_nr, msoa_counts_I.iloc[:,day2plot].tolist(), label='Infectious')
ax.plot(msoas_nr, msoa_counts_R.iloc[:,day2plot].tolist(), label='Recovered')
ax.set_xlabel('MSOA')  # Add an x-label to the axes.
ax.set_ylabel('Number of people')  # Add a y-label to the axes.
ax.set_title("Infections across MSOAs, day "+str(day2plot))  # Add a title to the axes.
ax.legend()  # Add a legend.

# Line plot of SEIR per MSOA summed across days
fig, ax = plt.subplots()  # Create a figure and an axes.
ax.plot(msoas_nr, msoa_counts_E.sum(axis = 1), label='Exposed') 
ax.plot(msoas_nr, msoa_counts_I.sum(axis = 1), label='Infectious')
ax.plot(msoas_nr, msoa_counts_R.sum(axis = 1), label='Recovered')
ax.set_xlabel('MSOA')  # Add an x-label to the axes.
ax.set_ylabel('Number of people')  # Add a y-label to the axes.
ax.set_title("Infections across MSOAs summed across days")  # Add a title to the axes.
ax.legend()  # Add a legend.
    
# heatmap SEIR
var2plot = msoa_counts_E
title4plot = "nr exposed"
xticklabels=days
xticks = xticklabels
xticks = [x +1 - 0.5 for x in xticks] # to get the tick in the centre of a heatmap grid rectangle
# pick one colourmap from below
#cmap = sns.color_palette("coolwarm", 128)  
cmap = 'RdYlGn_r'  
plt.figure(figsize=(30, 10))
ax1 = sns.heatmap(var2plot, annot=False, cmap=cmap, xticklabels=xticklabels)
ax1.set_xticks(xticks)
plt.title(title4plot)
plt.ylabel("MSOA")
plt.xlabel("Day")
plt.show()

    
# line plot dangers across time, summed per venue type
iloc[:,0:2]
test = home_dangers.iloc[:,1:nr_days+1].sum(axis=0)


fig, ax = plt.subplots()
#ax.plot(days, home_dangers.iloc[:,1:nr_days+1].sum(axis=0), label='Home') 
ax.plot(days, work_dangers.iloc[:,1:nr_days+1].sum(axis=0), label='Work')
ax.plot(days, retail_dangers.iloc[:,1:nr_days+1].sum(axis=0), label='Retail')
ax.plot(days, primaryschool_dangers.iloc[:,1:nr_days+1].sum(axis=0), label='Primary schools')
ax.plot(days, secondaryschool_dangers.iloc[:,1:nr_days+1].sum(axis=0), label='Secondary schools')
ax.set_xlabel('Days')  # Add an x-label to the axes.
ax.set_ylabel('Danger score')  # Add a y-label to the axes.
ax.set_title("Venue danger scores over time")  # Add a title to the axes.
ax.legend()  # Add a legend   




# geographical plots


# choropleth

# load in a shapefile
sh_file = os.path.join(data_dir, "MSOAS_shp","bcc21fa2-48d2-42ca-b7b7-0d978761069f2020412-1-12serld.j1f7i.shp")
map_df = gpd.read_file(sh_file)
# check
#map_df.plot()
# rename
map_df.rename(index=str, columns={'msoa11cd': 'Area'},inplace=True)

# merge spatial data and counts (created above)
msoa_counts_I['Area'] = msoa_counts_I.index
merged_data = pd.merge(map_df,msoa_counts_I,on='Area')

# set the range for the choropleth
vmin = 0
vmax = msoa_counts_I.iloc[:,0:nr_days].max().max()  # find max to scale (or set max number eg if using %)


# option 1
# create individual plots and save each as image
for d in range(0, 30):
    # set a variable that will call whatever column we want to visualise on the map
    variable = "Day"+str(d+1)
    
    # create figure and axes for Matplotlib
    fig, ax = plt.subplots(1, figsize=(10, 6))
    # create map
    merged_data.plot(column=variable, cmap='Blues', linewidth=0.8, ax=ax, edgecolor='0.8')
    # remove the axis
    ax.axis('off')
    # add a title
    ax.set_title('Infected cases day'+str(d+1), fontdict={'fontsize': '25', 'fontweight' : '3'})
    # Create colorbar as a legend
    sm = plt.cm.ScalarMappable(cmap='Blues', norm=plt.Normalize(vmin=vmin, vmax=vmax))
    # empty array for the data range
    sm._A = []
    # add the colorbar to the figure
    cbar = fig.colorbar(sm)
    
    fig.savefig('map_day'+str(d+1)+'.png', dpi=300)
    
# put all the images created above together using imageio
with imageio.get_writer('map_movie.gif', mode='I', duration=0.5) as writer:
    for d in range(0, 30):
        filename = "map_day"+str(d+1)+".png"
        image = imageio.imread(filename)
        writer.append_data(image)
        
# dots on map
#merged_data.crs # check coordinate system from underlay (here MSOAs - epsg:27700)

# Converting a Pandas object (Dataframe) to a GeoPandas object (Dataframe)
# Use for all:
crs = {'init': 'epsg:27700'}
# For primary schools:
geometry = [Point(xy) for xy in zip(primaryschools.bng_e, primaryschools.bng_n)]
primaryschools = primaryschools.drop(['bng_e', 'bng_n'], axis=1)
gdf_primaryschools = gpd.GeoDataFrame(primaryschools, crs=crs, geometry=geometry)
# For secondary schools:
geometry = [Point(xy) for xy in zip(secondaryschools.bng_e, secondaryschools.bng_n)]
secondaryschools = secondaryschools.drop(['bng_e', 'bng_n'], axis=1)
gdf_secondaryschools = gpd.GeoDataFrame(secondaryschools, crs=crs, geometry=geometry)
# For retail:
geometry = [Point(xy) for xy in zip(retail.bng_e, retail.bng_n)]
retail = retail.drop(['bng_e', 'bng_n'], axis=1)
gdf_retail = gpd.GeoDataFrame(retail, crs=crs, geometry=geometry)

# plot all retail locations
base = map_df.plot(color='white', edgecolor='black')
gdf_primaryschools.plot(ax=base, marker='o', color='blue', markersize=5, legend = True)
gdf_secondaryschools.plot(ax=base, marker='o', color='purple', markersize=5, legend = True)
gdf_retail.plot(ax=base, marker='o', color='red', markersize=5, legend = True)


# plot only those with certain level of danger
base = map_df.plot(color='white', edgecolor='black')
gdf_retail[gdf_retail.Danger0 > 0].plot(ax=base, marker='o', color='red', markersize=5)


# alternative way of plotting
fig, ax = plt.subplots()
# set aspect to equal (because we are not using *geopandas* plot)
ax.set_aspect('equal')
map_df.plot(ax=ax, color='white', edgecolor='black')
gdf_retail.plot(ax=ax, marker='o', color='red', markersize=5)
plt.show()

ax = gdf_retail.plot(color='k', zorder=2)
map_df.plot(ax=ax, zorder=1);

# geopandas heatmap from points
%matplotlib inline
pylab.rcParams['figure.figsize'] = 8, 6

pts = gdf_retail.GeoDataFrame.from_file('points_demo.shp')



