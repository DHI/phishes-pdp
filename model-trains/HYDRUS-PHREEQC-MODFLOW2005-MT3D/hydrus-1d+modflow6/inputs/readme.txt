run.bat permet de lancer Hydrus avec cmd


prepare_inputs.py
=> script Python pour créer les fichier d'entrées contenant à pas journalier de 1960 à 2019 :
- l'infiltration en mm/jour (selon Modèle Gardenia dans le Nord avec capacité progressive du sol de 100 mm)
		=> qu'il faudra convertir en cm (soit inf/10)
		=> si infiltration < 0.01, alors = 0mm
- les concentrations en nitrates associées (données Cassis) mg/L
		=> qu'il faudra convertir en mg/cm3 (soit C/1000)

reste à créer un fichier Python :
- capable de modifier/créer le fichier ATMOSPH.IN (mais il faudrait déjà qu'il fasse la même taille que mes données d'entrées (21915 jours)
- puis de lancer Hydrus avec run.bat (os command)
- puis de sortir les résultats avec Python 

