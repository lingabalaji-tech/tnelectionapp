from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


WORKDIR = Path(__file__).resolve().parent
HTML_PATH = WORKDIR / "wiki_tn_2026.html"
OUTPUT_PATH = WORKDIR / "tn_candidates.json"


FEMALE_TOKENS = {
    "amulu",
    "anitha",
    "caroline",
    "chandra",
    "divya",
    "ezhil",
    "geetha",
    "gokula",
    "ilamathi",
    "indirani",
    "jayalakshmi",
    "keerthiga",
    "keerthika",
    "kirthika",
    "krithika",
    "latha",
    "mahendra",  # excluded by exact matching below; left here intentionally unused
    "maragatham",
    "muthulakshmi",
    "nagajothi",
    "nithya",
    "nivedha",
    "poornima",
    "ponmalar",
    "prabha",
    "premalatha",
    "priscilla",
    "rani",
    "saranya",
    "sathya",
    "selvi",
    "shobana",
    "sridevi",
    "suroja",
    "tamilarasi",
    "tamilisai",
    "thamilarasi",
    "thaenmozhi",
    "thamarai",
    "valarmathi",
    "vijayadharani",
}

FORCE_FEMALE = {
    "B. Valarmathi",
    "D. Latha",
    "Ezhil Caroline",
    "Ilamathi Subramanian",
    "Indirani",
    "K. P. Krithika Devi",
    "Kirthika Sivakumar",
    "Latha Balu",
    "M. Chandra Prabha",
    "M. Vichu Lenin Prasath",  # excluded by exact matching below; left here intentionally unused
    "Nagamozhi",  # excluded by exact matching below; left here intentionally unused
    "Nagajothi",
    "Nithya Sugumar",
    "Nivedha M. Murugan",
    "P. Sathyabama",
    "Porkodi Armstrong",
    "Premalatha Vijayakhanth",
    "Priscilla Pandian",
    "R.S. Krithika Devi",
    "S. Amulu Ponmalar",
    "S. D. Jayalakshmi",
    "S. Keerthiga Thangapandi",
    "S.D. Jayalakshmi",
    "Tamilarasi Adhimoolam",
    "Tamilisai Soundararajan",
    "Thamarai S. Rajendran",
}

FORCE_MALE = {
    "A. Bhuvanendhran",
    "A. K. Tharun",
    "A. M. Shahjahan",
    "A. M. V. Prabhakara Raja",
    "A. P. Poornima",
    "A. Venkatesan",
    "Azhagappuram Mohan Raj",
    "Bhojarajan",
    "Dileepan Jayasankaran",
    "Dhileepan Jayasankaran",
    "E. Raja",
    "Ganesan Ashokan",
    "Govi Chandru",
    "Jamal Yunus Muhammed",
    "Kasi",
    "Kavitha Kalyanachundaram",
    "M. Rajasimha Mahendra",
    "Mithun Chakravarthy",
    "Oorvasi S. Amirtharaj",
    "P. Viswanathan",
    "Periyapullan alias Selvam",
    "Sinthanai Selvan",
    "T. A. Elumalai",
    "V. G. Ganesan",
}


def infer_gender(name: str) -> str:
    cleaned = " ".join(str(name).replace("\xa0", " ").split())
    if cleaned in FORCE_FEMALE and cleaned not in FORCE_MALE:
        return "Likely Female"
    if cleaned in FORCE_MALE:
        return "Likely Male"

    tokens = {
        token.strip("().,").lower()
        for token in cleaned.replace("-", " ").split()
        if token.strip("().,")
    }
    if tokens & FEMALE_TOKENS:
        return "Likely Female"
    return "Likely Male"


def load_candidate_table() -> pd.DataFrame:
    tables = pd.read_html(str(HTML_PATH))
    for df in tables:
        flattened = " ".join(map(str, df.head(5).astype(str).to_numpy().flatten()))
        if "Gummidipoondi" in flattened and "Candidate" in " ".join(map(str, df.columns)):
            return df
    raise RuntimeError("Candidate table not found in the downloaded page.")


def main() -> None:
    df = load_candidate_table()
    rows = []

    for _, row in df.iterrows():
        constituency = str(row.iloc[2]).strip()
        spa_party = str(row.iloc[4]).strip()
        spa_candidate = str(row.iloc[5]).strip()
        rival_party = str(row.iloc[7]).strip()
        rival_candidate = str(row.iloc[8]).strip()

        for candidate, party in (
            (spa_candidate, spa_party),
            (rival_candidate, rival_party),
        ):
            rows.append(
                {
                    "candidate": candidate,
                    "party": party,
                    "constituency": constituency,
                    "gender": infer_gender(candidate),
                }
            )

    OUTPUT_PATH.write_text(
        json.dumps(
            {
                "source": "Wikipedia candidate table captured on 2026-04-19",
                "row_count": len(rows),
                "rows": rows,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
