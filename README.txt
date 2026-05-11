Flight Data Analyzer v0.01


### Fonctionnement : 

Se référer au manuel utilisateur 


### Prérequis pour lancer en python

- Python 3.12.7
- PyQt6 
- pip


### Dépendances 

les dépendances se trouvent dans le fichier "requirements.txt" 

```bash
pip install -r requirements.txt


### Lancement 

python src/main.py

### Build standalone

Pour faire une version standalone utiliser pyinstaller (installé via le fichier requirements.txt). 
Attention ! Bien se mettre dans le venv avant de faire une build, sinon ça ne prend pas les dépendances en compte. 
Pour se mettre dans le venv : 
source ./venv/Scripts/activate 

Puis dans le dossier Source : 

pyinstaller VVA.spec --clean


