# YtParser

Outil Python pour transformer des compilations musicales YouTube en pistes
individuelles, nommées et taguées pour Jellyfin.

**État actuel : Jalon 1 terminé.** La commande `cut` découpe un fichier audio
local selon une tracklist YAML validée, par copie de flux (sans réencodage).
`plan`, le téléchargement, le tagging et le choix du format de sortie ne sont
pas encore implémentés.
Le périmètre est défini dans [PRD.md](PRD.md), la progression dans
[TASKS.md](TASKS.md).

## Démarrage rapide (PowerShell)

Prérequis : Git, [uv](https://docs.astral.sh/uv/) et FFmpeg (avec `ffprobe`).
Python 3.12 est choisi pour le développement ; le paquet exige Python 3.12+.
uv peut installer Python et crée l'environnement isolé `.venv`.

```powershell
winget install --id astral-sh.uv --exact --source winget --scope user
winget install --id Gyan.FFmpeg --exact --source winget --scope user
```

Ouvrir un **nouveau terminal** après l'installation pour actualiser le PATH.
Depuis le dossier du projet :

```powershell
uv sync --locked
uv run python --version
uv run yt-dlp --version
ffmpeg -version
ffprobe -version
uv run ytparser hello
uv run ytparser --help
```

Python et les dépendances sont isolés du reste du PC. `yt-dlp` est une
dépendance Python du projet, utilisable aussi comme bibliothèque, pas une
installation globale. Il n'est pas nécessaire d'activer `.venv` pour `uv run`.
Dans VS Code, sélectionner `.venv\Scripts\python.exe` comme interpréteur.

## Découper un fichier audio local

```powershell
uv run ytparser cut tracklist.yaml --audio compilation.mp3 --output pistes
```

- La tracklist suit le format YAML de [PRD.md](PRD.md) (`tracks` : numéro,
  début, fin, titre, artiste ; temps `hh:mm:ss` avec décimales possibles).
- Chaque piste est copiée sans réencodage et garde le format de la source :
  `01.mp3`, `02.mp3`… La commande affiche la correspondance numéro → titre.
- `--output` (`-o`) vaut `output` par défaut ; le dossier est créé au besoin.
- Rien n'est écrasé : si un fichier de destination existe déjà, la commande
  s'arrête avant toute découpe.
- La commande refuse une tracklist qui dépasse la durée du fichier audio
  de plus d'une seconde (tolérance pour les durées arrondies à la seconde).

La copie de flux est rapide et n'ajoute pas de perte, mais ses limites suivent
les trames du codec (environ 26 ms en MP3 à 44,1 kHz). En MP3, le début de
chaque extrait peut aussi perdre quelques dizaines de millisecondes de son
(réservoir de bits ; jusqu'à 67 ms mesurées sur UC1). Les mesures sont dans
la [comparaison UC1](docs/uc1-comparaison.md). Les noms `Artiste/Album/NN - Titre.ext`
et les tags arrivent au Jalon 4.

## Vérification

```powershell
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

Les tests d'initialisation sont locaux et ne téléchargent aucun contenu.
`uv.lock` est versionné pour rendre les installations reproductibles.
Les tests FFmpeg (`tests/adapter/ffmpeg/`) et ceux de la commande `cut`
génèrent un son synthétique dans un dossier temporaire, puis vérifient de
vraies découpes. Ils nécessitent `ffmpeg` (avec l'encodeur `libmp3lame`)
et `ffprobe` dans le PATH. `tests/test_cut_whole_tracklist.py` utilise les
médias locaux UC1, non versionnés : il est ignoré (*skipped*) s'ils manquent.

Le [mémo des commandes de développement](COMMANDES.md) explique les commandes
Python, pytest, Ruff et uv ; il est enrichi au fil du projet.
Le [guide audio](docs/audio.md) explique les échantillons, les trames, la
copie de flux, le réencodage et FFmpeg ; il est enrichi au fil des sujets audio.

## Architecture

- `src/ytparser/core/` : logique pure, sans réseau ni disque, avec tests unitaires.
- `src/ytparser/adapters/` : intégration de yt-dlp, FFmpeg, fichiers et tags.
- `src/ytparser/cli.py` : commandes Typer ; aucune logique métier.
- `tests/` : tests pytest.
- `.github/copilot-instructions.md` : démarrage rapide et règles pour les agents.

Les dépendances de tagging et d'analyse du signal seront ajoutées lors
des tâches concernées, sans alourdir le squelette initial.

## Mise à jour de yt-dlp

YouTube évolue régulièrement. Pour actualiser la dépendance et le verrou :

```powershell
uv lock --upgrade-package yt-dlp
uv sync --locked
uv run yt-dlp --version
uv run pytest
```

Relire puis versionner les changements de `uv.lock`. Ne pas utiliser
`yt-dlp -U` pour cette installation gérée par uv.

## Git sur un PC avec plusieurs comptes

Ce dossier possède son **propre dépôt Git**, indépendant du dépôt parent.
L'identité d'auteur (`user.name`, `user.email`) et les préférences HTTPS
sont configurées **localement** : ne pas modifier la configuration globale
pour travailler sur ce projet.

```powershell
git rev-parse --show-toplevel
git config --show-origin --get user.name
git config --show-origin --get user.email
git config --local --get credential.https://github.com.username
git remote -v
git var GIT_AUTHOR_IDENT
git ls-remote origin
```

L'auteur des commits n'est pas le compte d'authentification. Ici, HTTPS
utilise Git Credential Manager, avec un nom de compte GitHub ciblé et
`credential.https://github.com.useHttpPath=true` dans la configuration locale.
Si une connexion est nécessaire, remplacer `MON_COMPTE` par le compte voulu :

```powershell
git credential-manager github login --username MON_COMPTE --device
```

Vérifier dans le navigateur le compte qui autorise la connexion.
Ne jamais partager de jeton, code de connexion ni fichier d'identifiants.
GitHub CLI possède sa propre session : `gh auth status --hostname github.com`
permet de la vérifier, mais ne prouve pas à lui seul l'accès Git HTTPS.
Un `git ls-remote origin` réussi vérifie cet accès sans publier de fichiers ;
sur un dépôt vide, aucune sortie est normale.

Un agent doit demander l'accord avant chaque commit, push ou changement
de compte/remote. Ne jamais ajouter `.venv`, des secrets ou des fichiers
audio à Git.

## Formats prévus et usage

La v1 vise M4A (défaut), MP3 et Opus. Pour l'instant, `cut` conserve le
format du fichier source ; la sélection du format (`--format`) arrive au Jalon 5.
La lecture Opus sur iOS reste à tester ; aucune compatibilité réelle n'est
encore certifiée.

Utiliser uniquement des contenus pour lesquels le téléchargement et le
traitement sont autorisés, dans le respect des droits et des conditions
applicables. Les fichiers audio produits ne sont pas destinés à être
redistribués et sont exclus de Git.