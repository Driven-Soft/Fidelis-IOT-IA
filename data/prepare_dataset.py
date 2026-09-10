# -*- coding: utf-8 -*-
"""
Fidelis - Preparação do dataset de treinamento
==============================================
Os datasets originais do Kaggle (waqi786) têm estrutura correta, mas a coluna
de peso foi gerada aleatoriamente, sem relação com a raça. Este script
recalibra os pesos usando faixas de referência de peso adulto por raça
(literatura de padrões raciais: AKC/FCI para cães, TICA/CFA para gatos),
com ajuste por sexo, e unifica as duas espécies em um único CSV de treino.

Saída: fidelis_training_dataset.csv
Colunas: Especie, Breed, Age (Years), Weight (kg), Gender
"""
import numpy as np
import pandas as pd

rng = np.random.default_rng(42)  # reprodutível

# Faixas de peso adulto (kg) por raça — [min fêmea leve, max macho pesado]
DOG_RANGES = {
    "Airedale Terrier": (19, 29), "Akita": (32, 59), "Alaskan Malamute": (34, 43),
    "Australian Shepherd": (16, 32), "Basenji": (9, 11), "Beagle": (9, 14),
    "Belgian Malinois": (18, 36), "Bernese Mountain Dog": (32, 52),
    "Bichon Frise": (5, 8), "Bloodhound": (36, 50), "Border Collie": (12, 20),
    "Boston Terrier": (5, 11), "Boxer": (25, 32), "Bull Terrier": (22, 38),
    "Bulldog": (18, 25), "Cavalier King Charles Spaniel": (5, 8),
    "Chesapeake Bay Retriever": (25, 36), "Chihuahua": (1.5, 3),
    "Chinese Shar-Pei": (18, 30), "Cocker Spaniel": (9, 14.5),
    "Dachshund": (7, 15), "Doberman Pinscher": (27, 45),
    "Dogo Argentino": (35, 45), "French Bulldog": (8, 13),
    "German Shepherd": (22, 40), "Golden Retriever": (25, 34),
    "Great Dane": (45, 90), "Havanese": (3, 6), "Irish Setter": (24, 32),
    "Jack Russell Terrier": (6, 8), "Labrador Retriever": (25, 36),
    "Lhasa Apso": (5, 8), "Maltese": (3, 4), "Miniature Schnauzer": (5, 9),
    "Papillon": (2.5, 4.5), "Pekingese": (3, 6.5),
    "Pembroke Welsh Corgi": (10, 14), "Pomeranian": (1.5, 3.5),
    "Poodle": (20, 32), "Pug": (6, 8), "Rottweiler": (35, 60),
    "Saint Bernard": (55, 90), "Samoyed": (16, 30), "Schnauzer": (14, 20),
    "Shetland Sheepdog": (6, 12), "Shiba Inu": (8, 11), "Shih Tzu": (4, 7.2),
    "Siberian Husky": (16, 27), "Vizsla": (20, 30), "Weimaraner": (25, 40),
    "West Highland White Terrier": (6, 10), "Whippet": (11, 19),
    "Yorkshire Terrier": (2, 3.2),
}

CAT_RANGES = {
    "Abyssinian": (3, 5), "American Shorthair": (3.5, 7), "Balinese": (2.5, 5),
    "Bengal": (3.5, 7), "Birman": (3, 5.5), "British Shorthair": (4, 8),
    "Burmese": (3, 6), "Chartreux": (3, 7), "Cornish Rex": (2.5, 4.5),
    "Devon Rex": (2.5, 4.5), "Egyptian Mau": (3, 6),
    "Exotic Shorthair": (3.5, 6.5), "Himalayan": (3, 6),
    "Maine Coon": (4.5, 11), "Manx": (3.5, 5.5), "Munchkin": (2.5, 4),
    "Norwegian Forest": (4, 9), "Ocicat": (3.5, 7), "Oriental": (2.5, 5),
    "Persian": (3, 6.5), "Ragdoll": (4.5, 9), "Russian Blue": (3, 5.5),
    "Savannah": (5, 11), "Scottish Fold": (3, 6), "Siamese": (2.5, 5),
    "Siberian": (4, 9), "Singapura": (2, 3.5), "Sphynx": (3, 5.5),
    "Tonkinese": (2.5, 5.5), "Turkish Angora": (2.5, 5),
}


def calibrate_weight(breed: str, gender: str, ranges: dict) -> float:
    """Sorteia um peso plausível dentro da faixa da raça, ajustado por sexo.

    Fêmeas concentram-se nos ~65% inferiores da faixa; machos, nos ~65%
    superiores. A sobreposição no meio é intencional (biologicamente real).
    """
    lo, hi = ranges[breed]
    span = hi - lo
    if gender == "Female":
        w = rng.uniform(lo, lo + 0.65 * span)
    else:
        w = rng.uniform(lo + 0.35 * span, hi)
    return round(w, 1)


def prepare(csv_path: str, especie: str, ranges: dict) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    df = df.drop_duplicates().reset_index(drop=True)
    missing = set(df["Breed"]) - set(ranges)
    if missing:
        raise ValueError(f"Raças sem faixa de referência: {missing}")
    df["Weight (kg)"] = [
        calibrate_weight(b, g, ranges)
        for b, g in zip(df["Breed"], df["Gender"])
    ]
    df.insert(0, "Especie", especie)
    return df[["Especie", "Breed", "Age (Years)", "Weight (kg)", "Gender"]]


if __name__ == "__main__":
    dogs = prepare("dogs_dataset.csv", "Cachorro", DOG_RANGES)
    cats = prepare("cats_dataset.csv", "Gato", CAT_RANGES)
    out = pd.concat([dogs, cats], ignore_index=True)
    out.to_csv("fidelis_training_dataset.csv", index=False)
    print(f"OK: {len(out)} registros ({len(dogs)} cães, {len(cats)} gatos)")
    print(out.groupby(["Especie"])["Weight (kg)"].describe().round(1))
