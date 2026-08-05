
# Ce scripts est un modèle journalier sur le bassin du Vivier
# de 1958 à 2019
# a deux réservoirs souterrains pour l'eau et les nitrates
# on prend comme recharge la recharge simulée de 1990 à 2019 et on la duplique de 1960 à 1989

# on veut voir si on arrive à concentrer d'avantage le réservoir profond afin d'avoir une bonne saisonnalité
# ie. des concentrations qui diminuent l'été.

# ======================================================================================================================
# IMPORT PACKAGES
# ======================================================================================================================
import matplotlib.pyplot as plt
import numpy as np
import matplotlib.backends.backend_pdf

# packages required for violin plots
import pandas as pd

# packages required to plot the best model
import os
from datetime import datetime, timedelta


# full model dates
first_date_long = '01/01/1960'
last_date_long = '01/01/2020'
timestep = 1  # day
nb_modelstep_long = ((datetime.strptime(last_date_long, "%d/%m/%Y") - datetime.strptime(first_date_long, "%d/%m/%Y")) / timestep).days + 1

dates_model_long = []
dates_model_long.append(datetime.strptime(first_date_long, "%d/%m/%Y"))
current_date = datetime.strptime(first_date_long, "%d/%m/%Y")
while current_date != datetime.strptime(last_date_long, "%d/%m/%Y"):
    current_date = dates_model_long[-1] + timedelta(days=1)
    dates_model_long.append(current_date)



# upload recharge data, from 01/01/1990 to 31/12/2019
df_histo_clim = pd.read_csv('infiltration.csv', sep='\t', skiprows=0, encoding='cp1252')
rech = df_histo_clim['Infiltration']  # mm/jr

# upload nitrates fluxes (kg/ha/an) from 1955 to 2020
surplus_cassis = pd.read_csv('surplus_cassis.csv', sep=';', skiprows=0, encoding='cp1252',
                             nrows=2020-1955+1, usecols=[1])
surplus_cassis_0 = pd.DataFrame(surplus_cassis).to_numpy()[:, 0][5:-1]  # pour avoir de 1960 à 2020
surplus_cassis = surplus_cassis_0 * 1.0

# creation d'un signal journalier de 01/01/1955 à 31/12/2019

full_recharge = np.zeros(len(dates_model_long) - 1)  # m3/jr
full_nitrates_rech = np.zeros(len(dates_model_long) - 1)  # kg/ha/jr
day_cnt = 0
day_cnt_bis = 0  # pour quand on arrive au 01/01/1990
day_cnt_N = 0
day_cnt_bis_N = 0  # pour quand on arrive au 01/01/1990
for yy in range(1960, 2020):

    rech_annuelle = []

    if dates_model_long[day_cnt] == datetime(1990, 1, 1, 0, 0):
        day_cnt_bis = day_cnt + 0
        day_cnt_bis_N = day_cnt_N + 0

    while dates_model_long[day_cnt].year == yy:  # tant qu'on est dans l'année en cours

        if day_cnt != 10957:  # on saute le 31/12/1989 car il y a un jour de plus sur la période précédente
            # recharge
            full_recharge[day_cnt] = rech[day_cnt - day_cnt_bis]  # mm/jr
            rech_annuelle.append(full_recharge[day_cnt])
        day_cnt += 1

    while dates_model_long[day_cnt_N].year == yy:  # tant qu'on est dans l'année en cours

        if day_cnt_N != 10957:  # on saute le 31/12/1989 car il y a un jour de plus sur la période précédente

            # transformation des surplus annuels en surplus journalier en fonction de la recharge annuelle
            # le surplus annuel est réparti en sur chaque jour de recharge selon le ratio rech_jr/rech_annee

            ratio_recharge = rech[day_cnt_N - day_cnt_bis_N] / sum(rech_annuelle)
            full_nitrates_rech[day_cnt_N] = surplus_cassis[1960 - yy] * ratio_recharge  # kg/ha/jr

        day_cnt_N += 1

# check
# plt.figure()
# plt.plot(full_recharge/5, lw=1.5)
# plt.plot(full_nitrates_rech, lw=0.8)
# plt.show()
print("recharge moyenne : ", np.mean(full_recharge) * 365.25, ' mm/an')
print("flux de nitrates moyen : ", np.mean(full_nitrates_rech) * 365.25, 'kg/ha/an')
print("Concentration moyen en nitrates dans les input : ",
      np.mean(full_nitrates_rech)/np.mean(full_recharge) * 100 * 4.42857, " mgNO3/L")

# traitement de la recharge :
full_recharge[full_recharge < 1e-5] = 0

# save to csv
# convert array into dataframe
DF = pd.DataFrame(-full_recharge)  # < 0 for Hydrus
DF.index = dates_model_long[:-1]
DF = DF.set_axis(['infiltration'], axis=1)
DF.index.names = ['Date']
# save the dataframe as a csv file
DF.to_csv("inf_hydrus.csv")

# convert array into dataframe
DF = pd.DataFrame(np.where(full_recharge > 0.0, full_nitrates_rech/full_recharge * 100 * 4.42857, 0))  #mgNO3
DF.index = dates_model_long[:-1]
DF = DF.set_axis(['concentration'], axis=1)
DF.index.names = ['Date']
# save the dataframe as a csv file
DF.to_csv("conc_inf_no3_hydrus.csv")
