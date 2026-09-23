import requests
from bs4 import BeautifulSoup
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


# Haetaan Kouluruoka.fi
headers = {
    "User-Agent": "Mozilla/5.0 Mankolan-koulun-ruokabotti"
}

response = requests.get(
    URL,
    headers=headers,
    timeout=30
)

response.raise_for_status()

soup = BeautifulSoup(response.text, "html.parser")


# Selvitetään tämän päivän viikonpäivä
today = date.today()
weekday = WEEKDAYS[today.weekday()]


# Etsitään tämän päivän h2
day_heading = None

for h2 in soup.find_all("h2"):
    text = clean_text(h2.get_text(" ", strip=True)).lower()

    if text.startswith(weekday + " "):
        day_heading = h2
        break


if day_heading is None:
    raise Exception(
        f"Tämän päivän otsikkoa ei löytynyt: {weekday}"
    )


# Etsitään tämän päivän ensimmäinen "Lounas"
# Tämä on tärkeää:
# emme ota Kasvislounasta.
lunch_heading = None

for element in day_heading.find_all_next(["h2", "h3"]):

    # Jos seuraava päivä alkaa, lopetetaan
    if element.name == "h2":
        break

    text = clean_text(
        element.get_text(" ", strip=True)
    ).lower()

    if text.startswith("lounas"):
        lunch_heading = element
        break


if lunch_heading is None:
    raise Exception(
        f"Lounasta ei löytynyt päivälle: {weekday}"
    )


# Kouluruoka.fi:n HTML-rakenteessa
# varsinainen ruokalista on heti Lounas-otsikon jälkeen
# tekstinä ja sen jälkeen tulee Ravintotiedot-linkki.

menu = None

for sibling in lunch_heading.next_siblings:

    # Jos vastaan tulee uusi otsikko,
    # emme halua mennä seuraavaan osioon.
    if getattr(sibling, "name", None) in ["h2", "h3"]:
        break

    # Ravintotiedot-linkkiä ei oteta mukaan.
    if getattr(sibling, "name", None) == "a":
        break

    text = clean_text(str(sibling))

    if text:
        menu = text
        break


if not menu:
    raise Exception(
        f"Ruokaa ei löytynyt päivälle: {weekday}"
    )


# Varmistus, ettei Ravintotiedot päädy mukaan
menu = menu.replace("Ravintotiedot", "")
menu = menu.replace("[Ravintotiedot]", "")
menu = clean_text(menu)


if not menu:
    raise Exception("Ruokalista jäi tyhjäksi.")


# XML:ää varten erikoismerkit turvallisesti
menu_xml = escape(menu)


# Luodaan RSS/XML
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


# Tallennetaan XML
with open("ruoka.xml", "w", encoding="utf-8") as file:
    file.write(xml)


print("Päivämäärä:", today)
print("Päivä:", weekday)
print("Ruoka:", menu)
print("XML kirjoitettu tiedostoon ruoka.xml")
