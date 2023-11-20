import subprocess

def openUrlsInSafari(urls):
    script = 'tell application "Safari" to make new document\n'
    for url in urls:
        script += f'tell application "Safari" to tell front window to make new tab with properties {{URL:"{url}"}}\n'
    subprocess.run(["osascript", "-e", script])

urls = [
    "https://www.fpm-ag.de/de/fonds/smallmidcap",
    "https://www.union-investment.de/unideutschland_xs-DE0009750497-fonds-975049/?portrait=3",
    "https://www.dws.de/aktienfonds/de0005152409-dws-german-small-mid-cap-ld/",
    "https://www.mainfirst.com/de/home/mainfirst-fonds/aktienfonds/mainfirst-germany-fund/",
    "https://de.allianzgi.com/de-de/unsere-fonds/fonds/list/allianz-nebenwerte-deutschland-a-eur?nav=documents",
    "https://www.deka.de/privatkunden/fondsprofil?id=LU0923076540#struktur",
    "https://www.lupusalpha.de/produkte/fonds/lupus-alpha-smaller-german-champions-a/"]

openUrlsInSafari(urls)

