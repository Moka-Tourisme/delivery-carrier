# Parcours de validation : environnement de test Colissimo

Tâche moka.cloud #11480. Base : une base 18.0 avec les modules `delivery_roulier_laposte_fr` et leurs dépendances installés, un compte transporteur Colissimo (identifiants fictifs) rattaché au mode « Colissimo Domicile (FR + Europe) ».

Surfaces : back-office ; site web hors périmètre ; point de vente hors périmètre ; portail hors périmètre ; devis hors périmètre.

Une étiquette Colissimo ne se génère que depuis le bon de livraison, d'où le back-office seul.

Dimensions : un seul format d'étiquette rejoué à l'écran (PDF 10x15). Les formats ZPL et DPL sont couverts par la construction de l'étiquette, pas par une capture. Un colis et deux colis sur le même bon sont rejoués.

1. Ouvrir Inventaire > Configuration > Modes de livraison > « Colissimo Domicile (FR + Europe) ». Le bouton d'environnement affiche « Test ».
   Attendu : un bandeau jaune dit que Colissimo n'a pas de service de test et que les étiquettes sont simulées.
2. Passer le bouton en « Production ».
   Attendu : le bandeau disparaît.
3. Repasser en « Test », puis créer une commande de vente avec ce mode de livraison, la confirmer, mettre les produits en colis sur son bon de livraison et cliquer sur Valider.
   Attendu : le bon passe à Terminé, le numéro de suivi est `TEST-<id>-1`, une pièce jointe PDF porte la mention TEST, et le fil de discussion contient « Environnement de test : aucune demande n'a été envoyée à Colissimo… ». Aucune demande n'est partie vers Colissimo.
4. Refaire l'étape 3 avec deux colis sur le bon.
   Attendu : deux pièces jointes et deux numéros de suivi (`TEST-<id>-1;TEST-<id>-2`).
5. Refaire l'étape 3 avec un client sans rue.
   Attendu : un message d'erreur de saisie s'affiche, comme en production, et rien n'est généré.
6. En Production, valider un bon avec un compte aux identifiants fictifs.
   Attendu : Colissimo répond « Identifiant ou mot de passe incorrect » (la demande part bien vers le service réel).

À la mise en service : passer chacun des sept modes Colissimo en Production avant de produire de vraies étiquettes.
