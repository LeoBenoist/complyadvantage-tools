Règles de surveillance des transactions proposées


#: 2
Nom de la règle: Même payeur sur multiples cagnottes
Description (logique, seuils / fenêtre temporelle indicatifs): Un même payeur (identifié par IBAN ou carte) contribue à ≥ M cagnottes distinctes (ex. ≥ 4) gérées
par
des marchands différents sur 30 jours.
Pourquoi c'est pertinent pour HiPay: Indicateur de layering ou de fraude organisée utilisant des plateformes de type HelloAsso / Ulule pour ventiler des fonds.
Explicitement mentionné comme scénario d'intérêt par Myrielle.
Source: Notes
Preuve: hipay.md l. 83, 136
────────────────────────────────────────

#: 4
Nom de la règle: Dépassement de seuil marchand (single transaction)
Description (logique, seuils / fenêtre temporelle indicatifs): Toute transaction unique dépassant un seuil absolu calibré par catégorie de marchand (ex. > 5 000 €
pour un marchand retail standard, > 15 000 € pour iGaming).
Pourquoi c'est pertinent pour HiPay: L'approche par seuil a été explicitement demandée. Pertinent pour les marchands retail (pharmacies, supermarchés) dont le
profil
transactionnel est borné, mais aussi pour les agents PSP.
Source: Notes
Preuve: hipay.md l. 84, 138
────────────────────────────────────────
#: 6
Nom de la règle: Pic d'activité inhabituel vs. profil historique du marchand (velocity spike)
Description (logique, seuils / fenêtre temporelle indicatifs): Volume quotidien (en montant ou en nombre de transactions) d'un marchand dépasse > 3× sa moyenne
mobile sur 90 jours, sur une fenêtre de 3 jours consécutifs.
Pourquoi c'est pertinent pour HiPay: Outil actuel ML uniquement comportemental, mais sans scénario explicable. Une règle de velocity offre un signal clair et
auditables. Cohérent avec des marchands saisonniers (Roland Garros, Club Med) ou des marchands dont le compte a été compromis.
Source: Notes + Recherche web
Preuve: hipay.md l. 89–90 ;
https://www.globenewswire.com/news-release/2017/09/12/1118296/0/en/HiPay-Group-HiPay-Sentinel-fights-against-fraud-using-Artificial-Intelligence/
────────────────────────────────────────
