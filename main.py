import select
import socket
import sys
import queue
import random
import datetime

liste_pseudo_aleatoire = [
    "Poule",
    "Panda",
    "Roberto",
    "Bic",
    "Chien",
    "Chat",
    "Baleine",
    "Agent",
    "Docteur"
]

# Permet de générer un pseudo aléatoire
def genererPseudoAleatoire():
    numero = random.randint(1,999)
    maxIndex = random.randint(0, len(liste_pseudo_aleatoire)-1)
    return liste_pseudo_aleatoire[maxIndex] + "_" + str(numero)

# cette fonction permet de retirer \r\n d'une séquence de caratères reçu à partir d'un recv
def byteVersCommande(sequenceByte):
    sequenceByte = str(sequenceByte, "utf-8")
    sequenceByte = sequenceByte.replace("\r\n", "")
    return sequenceByte

# Cette fonction permet de définir le pseudo d'un client
def setPseudoClient(client, pseudo):
    ancien_pseudo = liste_utilisateur[client]
    liste_utilisateur[client] = pseudo
    if ancien_pseudo:
        envoyerMessageGlobal(ancien_pseudo + " est devenu "+ pseudo)
    else:
        envoyerMessageGlobal(str(client.getpeername()) + " est devenu " + pseudo)

# Permet d'envoyer un message à tout le monde
def envoyerMessageGlobal(message):
    message = "Global > " + message + "\r\n"
    for client in entrees:
        if client is not server:
            client.send(message.encode())

# Permet d'envoyer les anciens message à un client
def envoyerHistoriqueAncienMessages(client):
    if len(liste_messages) == 0: return 0
    client.send("----- Historique des anciens messages -----\r\n".encode())
    for message in liste_messages:
        client.send(message)
    client.send("----------\r\n".encode())

# permet d'afficher les commanded disponible à un client
def printCommandsToClient(client):
    if len(liste_commandes) == 0: return 0
    client.send("----- Liste des commandes disponible -----\r\n".encode())
    for commande in liste_commandes:
        client.send(commande.encode() + "\r\n".encode())
    client.send("----------\r\n".encode())

# Permet de retourner l'heure actuelle
def getCurrentTime():
    now = datetime.datetime.now()
    hour = '{:02d}'.format(now.hour)
    minute = '{:02d}'.format(now.minute)
    secondes = '{:02d}'.format(now.second)
    return '{}H{}'.format(hour, minute)

# Cette fonction prend en paramètre une chaine de caractère et doit commencer par "!"
# Son second paramètre est le client ayant fait la commande
# La méthode return True si on a bien executé une commande
# Et false sinon
def handleCommand(command, client):
    if(len(command) < 1): return True
    if command[0] != "!":
        return False
    command_explose = command.split(" ")
    commande = command_explose[0]
    commande = commande.replace("!", "")

    # Si aucune commande n'est enregistrée
    if len(liste_commandes) == 0:
        liste_commandes.append("pseudo")
        liste_commandes.append("online")
        liste_commandes.append("cmd")

    if commande == "pseudo":
        setPseudoClient(client, command_explose[1])
        return True
    if commande == "online":
        printOnlineClients(client)
        return True

    if commande == "cmd":
        printCommandsToClient(client)
        return True

    return False

# Fonction permettant d'afficher la liste des clients en ligne à un client donné en paramètre
def printOnlineClients(client):
    client.send("+++ Voici la liste des clients connectés: +++\r\n".encode())
    for _client in liste_utilisateur:
        client.send(liste_utilisateur[_client].encode() + b"\r\n")
    client.send("+++++++++++++++++++++".encode())


adresse_ip_serveur = "localhost"
port_serveur = 10243

if len(sys.argv) > 1:
    port_serveur = int(sys.argv[1])

nb_client_max = 5
# On crée le socket tcp/ip
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)


adresse_serveur = (adresse_ip_serveur, port_serveur)

print("On démarre sur l'adresse %s:%s" % adresse_serveur)
server.bind(adresse_serveur)


# On démarre le serveur
server.listen(nb_client_max)

# On définit les 3 cannaux de communications
# On y ajoute "server" car c'est le premier "client"
entrees = [server]

sorties = []

# Liste contenant les messages envoyé par les utilisateurs
liste_messages = []

user_count = 0

liste_utilisateur = {}

liste_commandes = []

# Chaque message doit apparemment être stoqué dans une file avant d'être envoyé
file_attente_envoie_message = {}

# On démarre la boucle
while entrees:
    # On attend de recevoir une entrée
    print('\n En attente d\'un évenement')
    readable, writeable, exceptional = select.select(entrees, sorties, entrees)

    for message in readable:

        # Le client a tenté de se connecter
        if message is server:
            # Un "readable" socket est prêt à accepter la connexion
            connexion, adresse_client = message.accept()
            print('Nouvelle connexion de', adresse_client)
            connexion.setblocking(0)
            # On ajoute la connexion aux entrées
            entrees.append(connexion)

            # On enregistre le client
            liste_utilisateur[connexion] = genererPseudoAleatoire()

            # On ajoute une file d'attente pour cette connexion
            file_attente_envoie_message[connexion] = queue.Queue()

            # On lui envoie les anciens messages
            envoyerHistoriqueAncienMessages(connexion)

            envoyerMessageGlobal(liste_utilisateur[connexion] + " vient de se connecter !")

        # Sinon, le client a envoyé des données
        else:
            donnee = message.recv(1024)
            # Si donnee n'est pas vide
            if donnee:
                # SI on a reçu des données, ça vaut dire qu'on a reçu un message
                print('On a recu "%s" par %s' % (str(donnee), message.getpeername()))

                # On regarde si le message reçu peut être traité comme une commande
                command = str(byteVersCommande(donnee))
                wasCommand = handleCommand(command, message)


                # On ajoute ">" au début du message pour afficher montrer que c'est un message reçu pour les clients
                donnee = b"[" + getCurrentTime().encode() + b"] " + liste_utilisateur[message].encode() + b" > " + donnee

                file_attente_envoie_message[message].put(donnee)
                # On ajoute un canal de sortie pour la réponse
                if message not in sorties and wasCommand == False:
                    sorties.append(message)
                    liste_messages.append(donnee)
            # Si il n'y a pas de données, ça veut dire que le client s'est déconnecté
            else:
                print('Fermeture d\'une connexion', 'car aucune donnée n\'a été reçu')
                # On arrête d'écouter les entrées du client
                if message in sorties:
                    sorties.remove(message)
                entrees.remove(message)
                message.close()

                # On supprime le message de la file
                del file_attente_envoie_message[message]

    # On gère maintenant les sorties
    for message in writeable:
        try:
            message_suivant = file_attente_envoie_message[message].get_nowait()
        except queue.Empty:
            # Aucun message en attente donc on arrête de vérifier si on peut écrire
            print('la file de ', message.getpeername(), 'est vide')
            sorties.remove(message)
        else:
            for connectee in entrees:
                # On ne veut pas envoyer le message au serveur, ni à celui qui a envoyé ce message
                if connectee is not server and connectee is not message:
                    print('On envoie %s à %s' % (str(message_suivant), connectee.getpeername()))
                    connectee.send(message_suivant)
