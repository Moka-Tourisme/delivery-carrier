# Parcours de validation : ajouter la livraison Colissimo sur un devis

Tâche moka.cloud #11480. Base : une base 18.0 avec `delivery_roulier_laposte_fr` installé, un client en France et un article avec un poids.

Surfaces : back-office (devis) ; site web hors périmètre ; point de vente hors périmètre ; portail hors périmètre.

Le site web calcule le prix de livraison par le même appel, mais ce parcours n'a été rejoué que sur le devis.

Dimensions : un seul mode rejoué à l'écran, « Colissimo Domicile (FR + Europe) ».

1. Dans le back-office, créer un devis pour le client avec un article, puis cliquer sur « Ajouter l'expédition ».
2. Choisir « Colissimo Domicile (FR + Europe) » et cliquer sur « Obtenir le tarif ».
   Attendu : aucun message d'erreur, le coût affiché est de 0,00. Avant la correction : « Erreur : ce mode de livraison n'est pas disponible. ».
3. Cliquer sur « Ajouter ».
   Attendu : une ligne « Colissimo Domicile (FR + Europe) » à 0,00 apparaît dans les lignes du devis.
4. Confirmer le devis.
   Attendu : le devis passe à « Commande client » et le bon de livraison créé reprend le mode Colissimo.

Le prix est à 0 car La Poste ne renvoie aucun tarif. Une grille de prix reste à saisir dans Odoo si le client veut facturer la livraison.
