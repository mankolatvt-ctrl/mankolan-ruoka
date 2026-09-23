import requests
from bs4 import BeautifulSoup, NavigableString
from datetime import date
from xml.sax.saxutils import escape
import re


URL = "https://kouluruoka.fi/menu/jyvaskyla_mankolankoulu/"

WEEKDAYS = [
    "maanantai",
    "tiistai",
    "keskiviikko",
    "torstai",
    "perjantai",
    "lauantai",
    "sunnuntai"
]


def clean_text(text):
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


# ---------------------------------------
# 1. Haetaan Kouluruoka.fi
# ---------------------------------------

headers = {
    "User-Agent": "Mozilla/5.0 Mankolan-koulun-ruokabotti"
}

response = requests.get(
    URL,
    headers=headers,
    timeout=30
)

response.raise_for_status()

# Pakotetaan UTF-8
response.encoding = "utf-8"

soup = BeautifulSoup(
    response.text,
    "html.parser"
)


# ---------------------------------------
# 2. Selvitetään tämän päivän päivä
# ---------------------------------------

today = date.today()
weekday = WEEKDAYS[today.weekday()]


# ---------------------------------------
# 3. Etsitään tämän päivän h2
# ---------------------------------------

day_heading = None

for h2 in soup.find_all("h2"):

    text = clean_text(
        h2.get_text(" ", strip=True)
    ).lower()

    if text.startswith(weekday + " "):
        day_heading = h2
        break


if day_heading is None:
    raise Exception(
        f"Tämän päivän otsikkoa ei löytynyt: {weekday}"
    )


# ---------------------------------------
# 4. Etsitään päivän normaali Lounas
# ---------------------------------------

lunch_heading = None

for element in day_heading.find_all_next(["h2", "h3"]):

    # Seuraava h2 tarkoittaa seuraavaa päivää
    if element.name == "h2":
        break

    text = clean_text(
        element.get_text(" ", strip=True)
    ).lower()

    # Otetaan ensimmäinen Lounas.
    # Näin Kasvislounasta ei oteta.
    if text.startswith("lounas"):
        lunch_heading = element
        break


if lunch_heading is None:
    raise Exception(
        f"Lounasta ei löytynyt päivälle: {weekday}"
    )


# ---------------------------------------
# 5. Haetaan VAIN ruoan tekstisisältö
# ---------------------------------------

menu = None

for sibling in lunch_heading.next_siblings:

    # Jos vastaan tulee uusi otsikko,
    # lopetetaan.
    if getattr(sibling, "name", None) in ["h2", "h3"]:
        break

    # Ravintotiedot-painiketta ei oteta.
    if getattr(sibling, "name", None) == "button":
        break

    # Jos kyseessä on HTML-elementti,
    # otetaan siitä vain näkyvä teksti.
    if hasattr(sibling, "get_text"):

        text = sibling.get_text(
            " ",
            strip=True
        )

    else:

        text = str(sibling)

    text = clean_text(text)

    if text:
        menu = text
        break


if not menu:
    raise Exception(
        f"Ruokaa ei löytynyt päivälle: {weekday}"
    )


# ---------------------------------------
# 6. Poistetaan mahdollinen Ravintotiedot
# ---------------------------------------

menu = menu.replace(
    "Ravintotiedot",
    ""
)

menu = clean_text(menu)


if not menu:
    raise Exception(
        "Ruokalista jäi tyhjäksi."
    )


# ---------------------------------------
# 7. Muutetaan teksti XML-turvalliseksi
# ---------------------------------------

menu_xml = escape(menu)


# ---------------------------------------
# 8. Luodaan RSS XML
# ---------------------------------------

xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Mankolan koulu - päivän ruoka</title>
    <link>{URL}</link>
    <description>Mankolan koulun päivän normaali lounas</description>

    <item>
      <title>{weekday.capitalize()} {today.day}.{today.month}.</title>
      <description>{menu_xml}</description>
    </item>

  </channel>
</rss>
"""


# ---------------------------------------
# 9. Tallennetaan ruoka.xml
# ---------------------------------------

with open(
    "ruoka.xml",
    "w",
    encoding="utf-8"
) as file:

    file.write(xml)


# ---------------------------------------
# 10. Tulostetaan mitä haettiin
# ---------------------------------------

print()
print("================================")
print("MANKOLAN KOULUN RUOKA")
print("================================")
print("Päivämäärä:", today)
print("Päivä:", weekday)
print()
print("Ruoka:")
print(menu)
print()
print("ruoka.xml päivitetty.")
print("================================")
