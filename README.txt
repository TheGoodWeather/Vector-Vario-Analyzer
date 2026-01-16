Flight Data Analyzer v1.4.1

05-09-2025 : Félix
17-08-2025 : Félix
06-07-2025 : Félix
11-06-2025 : Félix
27-0-2025 : Félix 
15-05-2025 : Félix
01-05-2025 : Félix 

### Fonctionnement : 

Se référer au manuel utilisateur 


### Prérequis pour lancer en python

- Python 3.9.11
- PyQt6 
- pip


### Dépendances 

les dépendances se trouvent dans le fichier "requirements.txt" 

```bash
pip install -r requirements.txt


### Lancement 

python source/main.py

### Build standalone

Pour faire une version standalone utiliser pyinstaller (installé via le fichier requirements.txt). 
Attention ! Bien se mettre dans le venv avant de faire une build, sinon ça ne prend pas les dépendances en compte. 
Pour se mettre dans le venv : 
source ./venv/Scripts/activate 

Puis dans le dossier Source : 
pyinstaller --onefile --add-data="mainwindow.ui;." --add-data="export.ui;." --add-data="reference.ui;." --icon="logo_inv.ico" main.py

Le fichier .exe se trouve dans le dossier flight_analizer\Source\dist 


### Structure


- `source/` : Codes sources de l'application
	-'Config' : Dossier incluant les fichiers configs
	- 'database.json' : la base de donnée en format json
	- 'main.py' : fichier main à lancer 
	- 'gui.py' : Fichier contenant tout le code IHM
	- 'moulinette.py' : Fonction permettant le traitement des données
	- 'mainwindow.uic' : Fichier UI graphique 
	- 'exportwindow.uic' : Fichier UI graphique 
	- 'database_handler.py': Fichier python pour gérer la base de donnée de façon indépendante
- `ressource/ : Dossier contenant la doc et les vols à analyser (input)
- `README.md` : 

Il y a 3 fichiers python : Le main , qui faut lancer, le gui.py qui définit toute la structure de l'IHM et moulinette.py qui permet de traiter les données brutes.
Il y a 2 fichiers uic. Ce sont les fichiers qui contiennent l'interface graphique (main window et export window). Ils sont chargés automatiquement dans gui.py. 

### Version


version 1.0.0  
date de sortie : 01-05-2025
description : Première version. Fonctionnalités de bases, traitement du fichier brut, analyse de la polaire et enregistrement des fichiers. 


version 1.1.0 
date de sortie : 15-05-2025 
description : ajout de la double analyse de vol. Affichage de l'erreur en live (+ barre d'erreur). Possibilité d'enregistrer les fichiers de données analysées et la polaire en .csv


version 1.1.1 
date de sortie : 23-05-2025
description : Ajout des spinboxes pour mieux régler l'affichage du graphique polaire
Ajout des valeurs supplémentaires (Alpha, Theta, DTheta, Roulis, Lacet, Rho) dans l'analyse 

version 1.2.1 
date de sortie : 14-06-2025
description : Ajout de la base de donnée , correction de bugs mineurs liés aux couleurs, ajout du responsive design, ajout de la fonction recherche dans BD pour load la référence

version 1.2.2 
date de sortie : 18-06-2025
description : Ajout du logging 

version 1.2.3 
date de sortie : 23-06-2025
description : amélioration du logging, ajout de la conversion d'unité en glide ratio et glide (°) , amélioration robustesse pour le loading des fichiers

version 1.2.4 STABLE
date de sortie : 30-06-2025
description : Correction des calculs liés à la finesse 

version 1.3.4 
date de sortie : 06-07-2025
description : Ajout du volet de comparaison des vols. Version non testée.

version 1.3.5 
date de sortie : 17-08-2025 
description : Retrait temporaire des barres d'erreurs. Ajout des courbes de fits , correction de bugs mineurs. 

version 1.4.1 
date de sortie : 05-09-2025 
description : Ajout du volet "manage", correction bugs changement d'unité et export , ROI ajustées automatiquement.