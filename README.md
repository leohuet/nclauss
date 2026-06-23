# Programme vidéo Raspberry Pi pour Nicolas Clauss

Document d'instruction relatif à l'installation du programme de lecture vidéo / contrôle OSC.

Pour chaque Pi, le username sera "clausspi" et le mot de passe "pi".

## Instructions

### Contrôle OSC depuis Max

Installer Max si pas déjà fait : https://cycling74.com/downloads

Dans le dossier Max se trouve le patch "clauss_max.maxpat". A l'ouverture, tout se lance automatiquement ( <!> dont l'audio <!> ), il y a juste plusieurs choses à ajouter / modifier :

1. Dans le dossier "media", déposer les fichiers audio sous les noms "random" pour l'audio du mode aléatoire et "synchronous" pour l'audio du mode synchrone.
2. Dans le patch Max, modifier si nécessaire l'adresse IP broadcast du réseau wifi. Elle correspond à la dernière addresse IP sur ton sous-réseau. Par exemple, si ton adresse IP est 192.168.10.32 et que le masque de sous-réseau est 255.255.0.0, l'adresse broadcast sera 192.168.255.255. 


### Installation de l'image disque sur la Raspberry Pi

Il faut pour ça d'abord bien sûr récupérer l'image (image.img) sur le lien que je t'ai envoyé.

Ensuite voici les différentes étapes pour la première Raspberry Pi :

1. Flasher l'image disque via Balena Etcher sur la carte SD.
2. Insérer la carte SD dans la Raspberry Pi et l'allumer.
3. A ce moment là, tu verras un écran vert arriver avec écrit "visage 3" par ex, c'est le programme qui se lance automatiquement, pour stopper le programme, branche un clavier sur la Pi et écrire (tu ne verras pas ce que tu écris) :
```bash
sudo systemctl stop myscript.service
```
4. Ensuite, pour ouvrir les préférences de la Raspberry Pi, tu peux écrire :
```bash
sudo raspi-config
```
Dans la fenêtre qui s'ouvre, tu peux aller dans "System Options" puis "Wireless LAN" pour configurer ton réseau wifi.
Enfin faire
```bash
sudo reboot
```

5. Une fois cette étape réalisée, tu peux accéder à la Pi à distance en ssh depuis ton ordinateur en faisant ssh username@hostname.
    Ici :
```bash
ssh clausspi@clausspi1.local
```
ou par exemple
```bash
ssh clausspi@192.168.1.100
```
Pour chaque Raspberry, tu pourras faire la même chose en changeant le hostname à chaque fois (voir plus loin dans le document).


### Copier les fichiers vidéos sur la Raspberry Pi

Comme je ne pouvais pas avoir d'environnement avec Bureau sur la Pi, il faut tout faire en ligne de commande.
En branchant ta clé USB, tu peux voir tout le contenu en faisant :
```bash
ls /media/nomdetacleusb
```
Ensuite, tu peux copier coller directement chaque dossier de catégorie avec les vidéos que tu veux dans chaque (par exemple, un dossier "dos" déjà fait avec 10 vidéos dedans).
Pour cela utilise cette commande :
```bash
cp -r /media/nomdetacleusb/nomdetondossier /home/clausspi/clauss/uploads
```
Pour vérifier que les fichiers sont bien copiés :
```bash
ls /home/clausspi/clauss/uploads/dossiercatégorie
```
Enfin tu pourras supprimer mes fichiers d'exemple depuis l'interface web.


### Dupliquer l'image disque sur les 15 Raspberry Pi

Là, je te laisse le choix de la marche à suivre. Soit utiliser mon image et devoir remettre le wifi sur chaque Raspberry, soit utiliser ta première Raspberry configurée pour recréer une nouvelle image qui sera ensuite dupliquée sur les autres Raspberry.

Dans tous les cas, il faut bien que chaque Raspberry ait son nom d'hôte unique, donc quand tu dupliques une sd, allume uniquement la nouvelle Raspberry.
En SSH (via l'adresse IP que tu peux retrouver sur Angry IP Scanner ou sur la page de configuration de ton routeur), va dans "raspi-config" puis "System Options", "Hostname". Là tu peux modifier le nom d'hôte et changer le numéro à chaque fois pour avoir clausspi*.local avec * de 1 à 15. 

