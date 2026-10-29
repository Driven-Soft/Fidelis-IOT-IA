# -*- coding: utf-8 -*-
"""
Fidelis - Normalização da raça informada no cadastro
====================================================
No app, a raça é texto livre de até 20 caracteres (PETS.Raca). Tutores e
veterinários escrevem "Yorkshire", "Pastor Alemão", "vira-lata" ou
"golden retriever", enquanto a base de referência usa os nomes oficiais
em inglês ("Yorkshire Terrier", "German Shepherd"...). Sem esta etapa,
esses pets cairiam no fallback da espécie mesmo tendo faixa aprendida.

A comparação ignora maiúsculas, acentos, hífens e espaços repetidos. Os
apelidos são separados por espécie: "siberiano" é gato; o cão é "husky".
"""
from __future__ import annotations

import re
import unicodedata

# Valores que significam "sem raça definida": avaliados pela faixa da espécie
SEM_RACA = {
    "srd", "sem raca", "sem raca definida", "vira lata", "viralata",
    "mestico", "misto", "mix", "mixed", "indefinida", "nao definida",
    "nao informada", "nenhuma",
}

# Nomes populares no Brasil -> nome da raça na base de referência
APELIDOS = {
    "Cachorro": {
        "airedale": "Airedale Terrier",
        "akita inu": "Akita",
        "malamute": "Alaskan Malamute",
        "malamute do alasca": "Alaskan Malamute",
        "pastor australiano": "Australian Shepherd",
        "pastor belga": "Belgian Malinois",
        "pastor belga malinois": "Belgian Malinois",
        "malinois": "Belgian Malinois",
        "boiadeiro bernes": "Bernese Mountain Dog",
        "bernese": "Bernese Mountain Dog",
        "bichon": "Bichon Frise",
        "bichon frisado": "Bichon Frise",
        "boston": "Boston Terrier",
        "buldogue": "Bulldog",
        "buldogue ingles": "Bulldog",
        "bulldog ingles": "Bulldog",
        "english bulldog": "Bulldog",
        "cavalier": "Cavalier King Charles Spaniel",
        "cavalier king charles": "Cavalier King Charles Spaniel",
        "chesapeake": "Chesapeake Bay Retriever",
        "shar pei": "Chinese Shar-Pei",
        "sharpei": "Chinese Shar-Pei",
        "cocker": "Cocker Spaniel",
        "cocker spaniel ingles": "Cocker Spaniel",
        "salsicha": "Dachshund",
        "teckel": "Dachshund",
        "doberman": "Doberman Pinscher",
        "dobermann": "Doberman Pinscher",
        "dogo": "Dogo Argentino",
        "buldogue frances": "French Bulldog",
        "bulldog frances": "French Bulldog",
        "pastor alemao": "German Shepherd",
        "golden": "Golden Retriever",
        "dogue alemao": "Great Dane",
        "havanes": "Havanese",
        "setter irlandes": "Irish Setter",
        "jack russell": "Jack Russell Terrier",
        "labrador": "Labrador Retriever",
        "lhasa": "Lhasa Apso",
        "maltes": "Maltese",
        "schnauzer miniatura": "Miniature Schnauzer",
        "schnauzer mini": "Miniature Schnauzer",
        "pequines": "Pekingese",
        "corgi": "Pembroke Welsh Corgi",
        "welsh corgi": "Pembroke Welsh Corgi",
        "spitz alemao": "Pomeranian",
        "lulu da pomerania": "Pomeranian",
        "rotweiler": "Rottweiler",
        "rottweiller": "Rottweiler",
        "sao bernardo": "Saint Bernard",
        "samoieda": "Samoyed",
        "pastor de shetland": "Shetland Sheepdog",
        "sheltie": "Shetland Sheepdog",
        "shiba": "Shiba Inu",
        "shihtzu": "Shih Tzu",
        "husky": "Siberian Husky",
        "husky siberiano": "Siberian Husky",
        "braco hungaro": "Vizsla",
        "westie": "West Highland White Terrier",
        "west highland": "West Highland White Terrier",
        "yorkshire": "Yorkshire Terrier",
        "yorkie": "Yorkshire Terrier",
    },
    "Gato": {
        "abissinio": "Abyssinian",
        "americano de pelo curto": "American Shorthair",
        "balines": "Balinese",
        "bengali": "Bengal",
        "sagrado da birmania": "Birman",
        "british": "British Shorthair",
        "britanico de pelo curto": "British Shorthair",
        "burmes": "Burmese",
        "cartuxo": "Chartreux",
        "cornish": "Cornish Rex",
        "devon": "Devon Rex",
        "mau egipcio": "Egyptian Mau",
        "exotico": "Exotic Shorthair",
        "exotico de pelo curto": "Exotic Shorthair",
        "himalaio": "Himalayan",
        "mainecoon": "Maine Coon",
        "noruegues da floresta": "Norwegian Forest",
        "bosque da noruega": "Norwegian Forest",
        "norwegian forest cat": "Norwegian Forest",
        "persa": "Persian",
        "azul russo": "Russian Blue",
        "savana": "Savannah",
        "fold escoces": "Scottish Fold",
        "scottish": "Scottish Fold",
        "siames": "Siamese",
        "siberiano": "Siberian",
        "sphinx": "Sphynx",
        "esfinge": "Sphynx",
        "tonquines": "Tonkinese",
        "angora": "Turkish Angora",
        "angora turco": "Turkish Angora",
    },
}


def _chave(texto: str) -> str:
    """Forma canônica para comparação: "Pastor-Alemão " -> "pastor alemao"."""
    sem_acento = unicodedata.normalize("NFKD", texto)
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    return re.sub(r"[\s\-_]+", " ", sem_acento).strip().casefold()


def normalizar_raca(raca: str | None, especie: str,
                    racas_conhecidas: list[str]) -> str | None:
    """Converte a raça digitada no nome usado pela base de referência.

    Devolve o nome oficial quando reconhece a raça (direto ou por apelido),
    None quando o pet é sem raça definida, ou o texto original quando a
    raça não está na base — nesse caso o serviço aplica o fallback.
    """
    if raca is None or not raca.strip():
        return None
    chave = _chave(raca)
    if chave in SEM_RACA:
        return None
    oficiais = {_chave(nome): nome for nome in racas_conhecidas}
    if chave in oficiais:
        return oficiais[chave]
    apelido = APELIDOS.get(especie, {}).get(chave)
    if apelido in racas_conhecidas:
        return apelido
    return raca.strip()
