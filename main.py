import select
import socket
import sys
import queue

adresse_ip_serveur = "localhost"
port_serveur = 10242

if len(sys.argv) > 1:
    port_serveur = int(sys.argv[1])

nb_client_max = 5
# On crée le socket tcp/ip
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# ON block le server ????
server.setblocking(0)

# On attache le server à un port
adresse_serveur = (adresse_ip_serveur, port_serveur)
print("On démarre sur l'adresse %s:%s" % adresse_serveur)
server.bind(adresse_serveur)

# On démarre le serveur
server.listen(nb_client_max)

# On définit les 3 cannaux de communications
# On y ajoute "server" car c'est le premier "client"
entrees = [server]

sorties = []

user_count = 0

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

            # On ajoute une file d'attente pour cette connexion
            file_attente_envoie_message[connexion] = queue.Queue()

        # Sinon, le client a envoyé des données
        else:
            donnee = message.recv(1024)
            # Si donnee n'est pas vide
            if donnee:
                # SI on a reçu des données, ça vaut dire qu'on a reçu un message
                print('On a recu "%s" par %s' % (donnee, message.getpeername()))

                # On ajoute ">" au début du message pour afficher montrer que c'est un message reçu pour les clients
                donnee = b"> " + donnee

                file_attente_envoie_message[message].put(donnee)
                # On ajoute un canal de sortie pour la réponse
                if message not in sorties:
                    sorties.append(message)
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



