import os
import re
import json
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, parse_qs
import webbrowser
from datetime import datetime
import xml.etree.ElementTree as ET

# Versuche ReportLab für PDF-Export zu laden
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    HAVE_REPORTLAB = True
except ImportError:
    HAVE_REPORTLAB = False

DEFAULT_HEADERS = {"User-Agent": "portafontium-downloader/GUI"}
FONT_DEFAULT = ("Calibri", 12)

DARK_BG = "#1e1e1e"
DARK_FG = "#e6e6e6"
DARK_ACCENT = "#3c3f41"

LANG = {
    "de": {
        "title": "📚 PortaFontium Downloader",
        "home": "🏠 Porta Fontium",
        "add_book": "➕ Buch hinzufügen",
        "delete_book": "🗑️ Buch löschen",
        "change_pages": "📄 Seiten ändern",
        "download": "⬇️ Herunterladen",
        "stop": "⏹️ Stopp",
        "reset": "🔄 Zurücksetzen",
        "save_list": "💾 Warteliste speichern",
        "load_list": "📂 Warteliste laden",
        "export_pdf": "📄 Zu PDF exportieren",
        "choose_dir": "📂 Zielordner auswählen",
        "book_url": "Buch-URL:",
        "target_dir": "Zielordner:",
        "pages": "Seiten:",
        "pages_hint": "(z.B. 1,5,8-10; leer = alle)",
        "waiting_list": "Warteliste:",
        "col_book": "Buch / Karte / Sonstiges",
        "col_pages": "Seite/n",
        "col_status": "Status",
        "global_progress": "Gesamtfortschritt:",
        "log_open": "📜 Log öffnen",
        "log_close": "📜 Log schließen",
        "error_no_book": "Keine Bücher in der Warteliste.",
        "error_no_url": "Bitte eine Buch-URL eingeben.",
        "error_no_selection": "Bitte mindestens ein Buch aus der Warteliste auswählen.",
        "save_log": "📄 Log speichern",
        "pdf_error_no_books": "Keine Bücher in der Warteliste – nichts zu exportieren.",
        "pdf_error_lib": "ReportLab ist nicht installiert.\nBitte installiere es mit:\n\npip install reportlab",
        "pdf_saved": "PDF erfolgreich gespeichert."
    },
    "en": {
        "title": "📚 PortaFontium Downloader",
        "home": "🏠 Porta Fontium",
        "add_book": "➕ Add Book",
        "delete_book": "🗑️ Delete Book",
        "change_pages": "📄 Change Pages",
        "download": "⬇️ Download",
        "stop": "⏹️ Stop",
        "reset": "🔄 Reset",
        "save_list": "💾 Save Waiting List",
        "load_list": "📂 Load Waiting List",
        "export_pdf": "📄 Export to PDF",
        "choose_dir": "📂 Choose Directory",
        "book_url": "Book URL:",
        "target_dir": "Target Directory:",
        "pages": "Pages:",
        "pages_hint": "(e.g. 1,5,8-10; empty = all)",
        "waiting_list": "Waiting List:",
        "col_book": "Book / Map / Other",
        "col_pages": "Page(s)",
        "col_status": "Status",
        "global_progress": "Overall Progress:",
        "log_open": "📜 Open Log",
        "log_close": "📜 Close Log",
        "error_no_book": "No books in the waiting list.",
        "error_no_url": "Please enter a book URL.",
        "error_no_selection": "Please select at least one book from the waiting list.",
        "save_log": "📄 Save log",
        "pdf_error_no_books": "No books in the waiting list – nothing to export.",
        "pdf_error_lib": "ReportLab is not installed.\nPlease install it with:\n\npip install reportlab",
        "pdf_saved": "PDF saved successfully."
    },
    "cs": {
        "title": "📚 PortaFontium Downloader",
        "home": "🏠 Porta Fontium",
        "add_book": "➕ Přidat knihu",
        "delete_book": "🗑️ Smazat knihu",
        "change_pages": "📄 Změnit stránky",
        "download": "⬇️ Stáhnout",
        "stop": "⏹️ Zastavit",
        "reset": "🔄 Reset",
        "save_list": "💾 Uložit seznam",
        "load_list": "📂 Načíst seznam",
        "export_pdf": "📄 Exportovat do PDF",
        "choose_dir": "📂 Vybrat složku",
        "book_url": "URL knihy:",
        "target_dir": "Cílová složka:",
        "pages": "Stránky:",
        "pages_hint": "(např. 1,5,8-10; prázdné = všechny)",
        "waiting_list": "Seznam:",
        "col_book": "Kniha / Mapa / Jiný",
        "col_pages": "Stránky",
        "col_status": "Stav",
        "global_progress": "Celkový průběh:",
        "log_open": "📜 Otevřít log",
        "log_close": "📜 Zavřít log",
        "error_no_book": "Žádné knihy v seznamu.",
        "error_no_url": "Zadejte prosím URL knihy.",
        "error_no_selection": "Vyberte alespoň jednu knihu ze seznamu.",
        "save_log": "📄 Uložit log",
        "pdf_error_no_books": "Žádné knihy v seznamu – nic k exportu.",
        "pdf_error_lib": "ReportLab není nainstalován.\nNainstalujte jej příkazem:\n\npip install reportlab",
        "pdf_saved": "PDF bylo úspěšně uloženo."
    }
}

# Bekannte Buchtypen von Porta fontium und ihre Übersetzungen
DOC_TYPES = {
    "birth": {
        "de": "Geburtsmatrik",
        "cs": "Matrika narozených",
        "en": "Birth register",
        "aliases": ["narozen", "gebor", "geburt", "birth", "nativ"]
    },
    "baptism": {
        "de": "Taufmatrik",
        "cs": "Matrika křtěných",
        "en": "Baptism register",
        "aliases": ["křt", "krt", "tauf", "bapt", "baptism"]
    },
    "marriage": {
        "de": "Trauungsmatrik",
        "cs": "Matrika oddaných",
        "en": "Marriage register",
        "aliases": ["odd", "svatb", "trau", "hochzeit", "marri"]
    },
    "death": {
        "de": "Sterbematrik",
        "cs": "Matrika zemřelých",
        "en": "Death register",
        "aliases": ["zemř", "tod", "sterb", "death", "umrt"]
    },
    "index": {
        "de": "Index",
        "cs": "Rejstřík",
        "en": "Index",
        "aliases": ["rejst", "register", "index", "seznam"]
    },
    "map": {
        "de": "Karte",
        "cs": "Mapa",
        "en": "Map",
        "aliases": ["map", "kart", "plán", "geogr"]
    },
    "photo": {
        "de": "Foto",
        "cs": "Fotografie",
        "en": "Photograph",
        "aliases": ["foto", "photo", "fotografie", "bild"]
    },
    "document": {
        "de": "Dokument",
        "cs": "Dokument",
        "en": "Document",
        "aliases": ["dokument", "listina", "acta", "spis", "document"]
    },
    "chronicle": {
        "de": "Chronik",
        "cs": "Kronika",
        "en": "Chronicle",
        "aliases": ["kronik", "chron", "dějiny", "history"]
    },
    "military": {
        "de": "Militärliste",
        "cs": "Vojenský seznam",
        "en": "Military register",
        "aliases": ["voj", "milit", "regiment", "soldat"]
    },
    "census": {
        "de": "Volkszählung",
        "cs": "Sčítání lidu",
        "en": "Census",
        "aliases": ["scit", "zähl", "census", "popis"]
    },
    "tax": {
        "de": "Steuerliste",
        "cs": "Daňový seznam",
        "en": "Tax register",
        "aliases": ["tax", "dan", "steuer", "popl"]
    },
}


def sanitize_name(name: str) -> str:
    name = str(name or "").strip()

    # zu lang? kürzen
    if len(name) > 120:
        name = name[:120]

    # unerlaubte Zeichen
    name = re.sub(r'[\\/:*?"<>|]', "_", name)

    # überschüssige Leerzeichen
    name = re.sub(r"\s+", " ", name)

    # Leerzeichen in _
    name = name.replace(" ", "_")

    return name or "Unbenannt"


def is_porta_fontium(url: str) -> bool:
    return "portafontium.eu" in url


def fetch_html(url, session):
    r = session.get(url, timeout=20)
    r.raise_for_status()
    return r.text


def find_iip_links(html, base_url):
    soup = BeautifulSoup(html, "html.parser")

    # 1) GDA IIIF image detection (Porta Fontium Foto pages)
    m = re.search(r'https://www\.gda\.bayern\.de/digitalisat/(?:iiif|jpeg)/[^"\s]+', html)
    if m:
        return [m.group(0)]

    # 2) METS link detection (DFG viewer style)
    mets = re.search(r'https://www\.gda\.bayern\.de/mets/[0-9a-f-]+', html)
    if mets:
        return extract_dfg_images(mets.group(0))

    # 3) direct DFG viewer embed
    if ("dfg-viewer.de" in base_url):
        return extract_dfg_images(base_url)

    # 4) classic Porta Fontium images
    links = []
    tags = soup.find_all(["a", "img"])
    for tag in tags:
        attr = tag.get("href") or tag.get("src")
        if not attr:
            continue
        if any(x in attr for x in ["iipsrv", "fcgi-bin", ".jp2"]):
            links.append(urljoin(base_url, attr))

    return list(dict.fromkeys(links))


def extract_dfg_images(url):
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
    except:
        return []

    # Find IIIF image link inside JSON block
    m = re.search(r'https://www\.gda\.bayern\.de/digitalisat/iiif/[0-9a-f-]+/[0-9]+', r.text)
    if m:
        return [m.group(0)]

    return []


def build_download_url(iip_url):
    parsed = urlparse(iip_url)
    qs = parse_qs(parsed.query)
    fif = qs.get("FIF", [None])[0]
    if not fif:
        return iip_url
    base = parsed.scheme + "://" + parsed.netloc + parsed.path
    return f"{base}?FIF={fif}&cvt=jpeg&Q=90"


def parse_pf_metadata(html: str, url: str) -> dict:
    """
    Spezieller Parser für Porta fontium.
    Liest u.a.:
      - Ort (Místo / Ort)
      - Buchtyp (Material / Form -> Typ)
      - Jahresbereich (Laufzeit / Datace)
      - Übersetzte Buchtypen: type_de, type_cz, type_en
    """
    soup = BeautifulSoup(html, "html.parser")
    meta = {
        "source": "Porta fontium",
        "url": url,
    }

    # Sprache
    html_tag = soup.find("html")
    if html_tag:
        lang = html_tag.get("xml:lang") or html_tag.get("lang")
        if lang:
            meta["lang"] = lang

    # Titel finden
    title = None

    # 1) H1 bevorzugt
    h1 = soup.find("h1", id="page-title") or soup.find("h1", class_="title")
    if h1:
        title = h1.get_text(strip=True)

    # 2) Fallback: <meta property="og:title">
    if not title:
        og = soup.find("meta", property="og:title")
        if og and og.get("content"):
            title = og["content"].strip()

    # 3) Fallback: echter <title> TAG, aber NIE zu lang
    if not title:
        if soup.title and soup.title.string:
            t = soup.title.string.strip()
            if len(t) < 200:  # verhindern von HTML-Schrott
                title = t

    # 4) Finaler Fallback
    if not title:
        title = "Unbenannt"

    meta["title"] = title

    # ---------- ORT ----------
    place = None
    place_field = soup.select_one(".field-name-field-doc-place .field-items")
    if place_field:
        strongs = [s.get_text(" ", strip=True)
                   for s in place_field.select("strong")
                   if s.get_text(strip=True)]
        if strongs:
            place = ", ".join(strongs)
        else:
            place = place_field.get_text(" ", strip=True)

    if not place:
        for label_text in ("Místo:", "Místo", "Ort:", "Ort"):
            label = soup.find(
                lambda tag: tag.name in ("div", "span", "th", "td")
                            and label_text in tag.get_text()
            )
            if label and label.parent:
                full = label.parent.get_text(" ", strip=True)
                rest = full.replace(label_text, "").strip(" :\u00a0")
                if rest:
                    place = rest
                    break

    if place:
        meta["place"] = place

    # ---------- BUCHTYP ----------
    type_items = []

    type_block = soup.select_one(".field-name-field-register-type")
    if type_block:
        for itm in type_block.select(".field-item"):
            t = itm.get_text(" ", strip=True)
            if t:
                type_items.append(t)

    if not type_items:
        for fld in soup.select(".field"):
            label = fld.select_one(".field-label")
            if not label:
                continue
            if "typ" in label.get_text(" ", strip=True).lower():
                for itm in fld.select(".field-item"):
                    t = itm.get_text(" ", strip=True)
                    if t:
                        type_items.append(t)
                if type_items:
                    break

    if type_items:
        seen = set()
        unique = []
        for t in type_items:
            if t not in seen:
                unique.append(t)
                seen.add(t)
        book_type = " | ".join(unique)
        meta["book_type"] = book_type
        # Haupttyp: erster Eintrag vor " | "
        primary_type = unique[0]
    else:
        # URL-Logik für Karten, Fotos & mehr
        u = url.lower()
        if "/map/" in u:
            primary_type = "map"
        elif "/photo/" in u:
            primary_type = "photo"
        else:
            primary_type = "Matrik"  # fallback
        meta["book_type"] = primary_type

    # Übersetzungen aus TYPE_TRANSLATIONS
    def match_doc_type(primary_type):
        text = primary_type.lower()

        # 1. direktes Schlüsselwortmatching
        for key, data in DOC_TYPES.items():
            if key in text:
                return data

        # 2. Alias Matching
        for key, data in DOC_TYPES.items():
            if any(alias in text for alias in data["aliases"]):
                return data

        # 3. Sprach-Matching
        for key, data in DOC_TYPES.items():
            if data["cs"].lower() in text:
                return data
            if data["de"].lower() in text:
                return data
            if data["en"].lower() in text:
                return data

        # 4. Fallback
        return {
            "de": primary_type,
            "cs": primary_type,
            "en": primary_type
        }

    match = match_doc_type(primary_type)

    meta["type_de"] = match["de"]
    meta["type_cz"] = match["cs"]
    meta["type_en"] = match["en"]

    # ---------- DATEN (Laufzeit / Datace) ----------
    date_text = None

    date_field = soup.select_one(".field-name-field-doc-dates .field-item")
    if date_field:
        date_text = date_field.get_text(" ", strip=True)

    if not date_text:
        candidate = soup.find(
            string=lambda s: s and "-" in s and any(ch.isdigit() for ch in s)
        )
        if candidate:
            date_text = candidate.strip()

    if date_text:
        meta["date_raw"] = date_text
        years = re.findall(r"(\d{3,4})", date_text)
        if len(years) >= 2:
            meta["year_from"], meta["year_to"] = years[0], years[1]
        elif len(years) == 1:
            meta["year_from"] = meta["year_to"] = years[0]

    # ---------- Material-Block für Log ----------
    material_section = None
    for legend_label in ("Materiál / forma", "Material / Form", "Materiál / form",
                         "Materiál / Forma", "Material / forma"):
        leg = soup.find(
            "legend",
            string=lambda t: t and legend_label.lower() in t.lower()
        )
        if leg:
            material_section = leg.find_parent("fieldset")
            if material_section:
                break

    if material_section:
        meta["material_section_text"] = material_section.get_text(
            "\n", strip=True
        )

    return meta


def parse_generic_metadata(html: str, url: str) -> dict:
    """
    Fallback-Parser für andere Seiten.
    Versucht nur Titel + ein paar Jahreszahlen.
    """
    soup = BeautifulSoup(html, "html.parser")
    meta = {"source": "generic", "url": url}

    title = soup.title.string.strip() if soup.title and soup.title.string else None
    if title:
        meta["title"] = title

    text = soup.get_text(" ", strip=True)
    years = re.findall(r"\b(1[5-9]\d{2}|20[0-2]\d)\b", text)
    if years:
        meta["year_from"] = years[0]
        meta["year_to"] = years[-1]

    # generische Typ-Bezeichnungen
    meta["book_type"] = "Dokument"
    meta["type_de"] = "Dokument"
    meta["type_cz"] = "Dokument"
    meta["type_en"] = "Document"

    return meta


def download_image(url, path, session, retries=3):
    for attempt in range(retries):
        try:
            r = session.get(url, stream=True, timeout=60)
            r.raise_for_status()
            with open(path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            return True
        except Exception:
            if attempt == retries - 1:
                return False


class Downloader:
    def __init__(self, books, log_callback=None, progress_callback=None,
                 stop_flag=lambda: False, save_metadata=False):
        self.books = books
        self.log = log_callback or (lambda msg: None)
        self.progress_update = progress_callback or (lambda idx, val: None)
        self.stop_flag = stop_flag
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)
        self.save_metadata = save_metadata

    def parse_pages(self, pages_str, total):
        if not pages_str.strip():
            return list(range(1, total + 1))
        pages = []
        for part in pages_str.split(","):
            part = part.strip()
            if "-" in part:
                try:
                    a, b = map(int, part.split("-"))
                    pages.extend(i for i in range(a, b + 1) if 1 <= i <= total)
                except Exception:
                    pass
            else:
                try:
                    i = int(part)
                    if 1 <= i <= total:
                        pages.append(i)
                except Exception:
                    pass
        return sorted(set(pages))

    def run(self):
        total_books = len(self.books)
        books_done = 0

        for idx, book in enumerate(self.books):
            if self.stop_flag():
                self.log("[*] Abgebrochen.")
                self.progress_update(idx, "❌")
                break

            url = book["url"]

            try:
                html = fetch_html(url, self.session)
                links = find_iip_links(html, url)

                if is_porta_fontium(url):
                    meta = parse_pf_metadata(html, url)
                else:
                    meta = parse_generic_metadata(html, url)

            except Exception as e:
                self.log(f"[!] Fehler beim Laden von {url}: {e}")
                links = []
                meta = {}

            if not links:
                self.log(f"[!] Keine Seiten für {url}")
                self.progress_update(idx, "⚠️")
                books_done += 1
                self.progress_update("global", books_done / total_books * 100)
                continue

            # --- METADATEN AUSWERTEN ---

            # Ort -> Oberordner
            place_raw = meta.get("place") or meta.get("title") or "Unknown"
            top_folder = sanitize_name(place_raw)

            # Buchtyp DE/CZ/EN
            type_de = sanitize_name(meta.get("type_de", meta.get("book_type", "Unbekannt")))
            type_cz = sanitize_name(meta.get("type_cz", "Matrika"))
            type_en = sanitize_name(meta.get("type_en", "Register"))

            type_triplet = f"{type_de}-{type_cz}-{type_en}"

            # Titel für Foto / Karte
            title_raw = sanitize_name(meta.get("title", ""))

            # Typprüfung
            is_map = (type_de == "Karte")
            is_photo = (type_de == "Foto")

            # Jahresbereich
            year_from = meta.get("year_from")
            year_to = meta.get("year_to")
            if year_from and year_to and year_from != year_to:
                year_span = f"{year_from}-{year_to}"
            elif year_from:
                year_span = year_from
            else:
                year_span = ""

            # Unterordner bestimmen
            if (is_map or is_photo) and title_raw:
                sub_folder_raw = f"{type_de}_{title_raw}"
                if year_span:
                    sub_folder_raw += f"_{year_span}"
            else:
                if year_span:
                    sub_folder_raw = f"{type_triplet}_{year_span}"
                else:
                    sub_folder_raw = type_triplet

            sub_folder = sanitize_name(sub_folder_raw)

            base_outdir = book["outdir"] or os.getcwd()
            full_outdir = os.path.join(base_outdir, top_folder, sub_folder)
            os.makedirs(full_outdir, exist_ok=True)

            # --- Metadaten speichern ---
            if self.save_metadata:
                metadata_lines = [
                    f"URL: {url}",
                    f"Titel: {meta.get('title', '')}",
                    f"Ort: {place_raw}",
                    f"Buchtyp (DE): {type_de}",
                    f"Buchtyp (CZ): {type_cz}",
                    f"Buchtyp (EN): {type_en}",
                    f"Roh-Typfeld: {meta.get('book_type', '')}",
                    f"Zeitraum: {year_span or meta.get('date_raw', '')}",
                    f"Gesamtseiten (gefunden): {len(links)}",
                    f"Gewählte Seiten: {book.get('pages', 'ALLE')}",
                    f"Downloadzeit: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                ]
                if "material_section_text" in meta:
                    metadata_lines.append("")
                    metadata_lines.append("=== Material / Form (vollständig) ===")
                    metadata_lines.append(meta["material_section_text"])

                metadata_text = "\n".join(metadata_lines)
                meta_file = os.path.join(full_outdir, "metadata.txt")
                try:
                    with open(meta_file, "w", encoding="utf-8") as f:
                        f.write(metadata_text)
                    self.log(f"[ℹ️] Metadaten gespeichert: {meta_file}")
                except Exception as e:
                    self.log(f"[!] Fehler beim Schreiben der Metadaten: {e}")

            # --- Seiten downloaden ---
            pages_to_download = self.parse_pages(book.get("pages", ""), len(links))
            errors = 0

            for i in pages_to_download:
                if self.stop_flag():
                    errors += 1
                    break

                link = links[i - 1]

                # Bildnamen
                if (is_map or is_photo) and title_raw:
                    fname_raw = f"{type_de}_{title_raw}_{i:04d}.jpg"
                else:
                    fname_raw = f"{type_triplet}_{i:04d}.jpg"

                fname = sanitize_name(fname_raw)
                outpath = os.path.join(full_outdir, fname)

                dl_url = build_download_url(link)
                self.log(f"Lade {fname} -> {outpath}")
                ok = download_image(dl_url, outpath, self.session)
                if not ok:
                    errors += 1

            if errors == 0:
                self.progress_update(idx, "✅")
            elif errors < len(pages_to_download):
                self.progress_update(idx, "⚠️")
            else:
                self.progress_update(idx, "❌")

            books_done += 1
            self.progress_update("global", books_done / total_books * 100)

        self.log("[*] Alle Bücher fertig.")


# --- GUI ---

class DownloaderGUI:
    def __init__(self, master):
        self.master = master
        self.lang = "de"
        self.books = []
        self.stop_flag = False
        self.log_open = False
        self.log_lines = []

        master.title(LANG[self.lang]["title"])
        master.geometry("1130x850")

        master.configure(bg=DARK_BG)
        style = ttk.Style(master)
        style.theme_use("default")
        style.configure("Treeview",
                        background=DARK_BG,
                        fieldbackground=DARK_BG,
                        foreground=DARK_FG,
                        rowheight=24)
        style.configure("Treeview.Heading",
                        background=DARK_ACCENT,
                        foreground="white")
        master.tk_setPalette(background=DARK_BG, foreground=DARK_FG, activeBackground="#444")

        top_frame = tk.Frame(master, bg=DARK_BG)
        top_frame.pack(fill="x", pady=5)

        self.btn_home = tk.Button(top_frame, text=LANG[self.lang]["home"], font=FONT_DEFAULT,
                                  bg="#1E90FF", fg="white", command=self.open_home)
        self.btn_home.pack(side="left", padx=5)

        self.lang_var = tk.StringVar(value=self.lang)
        for l in ["de", "en", "cs"]:
            tk.Radiobutton(top_frame, text=l.upper(), variable=self.lang_var, value=l,
                           command=self.change_language, bg=DARK_BG, fg=DARK_FG,
                           selectcolor=DARK_BG).pack(side="left")

        self.btn_log_toggle = tk.Button(top_frame, text=LANG[self.lang]["log_open"], font=FONT_DEFAULT,
                                        bg="#6c757d", fg="white", command=self.toggle_log)
        self.btn_log_toggle.pack(side="right", padx=5)

        self.save_log_var = tk.BooleanVar(value=False)
        self.chk_save_log = tk.Checkbutton(top_frame, text=LANG[self.lang]["save_log"],
                                           variable=self.save_log_var, font=FONT_DEFAULT,
                                           bg=DARK_BG, fg=DARK_FG, selectcolor=DARK_BG)
        self.chk_save_log.pack(side="right", padx=5)

        frame_top = tk.Frame(master, bg=DARK_BG)
        frame_top.pack(fill="x", padx=10, pady=5)

        self.lbl_url = tk.Label(frame_top, text=LANG[self.lang]["book_url"],
                                font=FONT_DEFAULT, bg=DARK_BG, fg=DARK_FG)
        self.lbl_url.grid(row=0, column=0, sticky="w", padx=5)
        self.url_entry = tk.Entry(frame_top, width=60, font=FONT_DEFAULT,
                                  bg="#2b2b2b", fg=DARK_FG, insertbackground=DARK_FG)
        self.url_entry.grid(row=0, column=1, padx=5, pady=2)

        self.lbl_outdir = tk.Label(frame_top, text=LANG[self.lang]["target_dir"],
                                   font=FONT_DEFAULT, bg=DARK_BG, fg=DARK_FG)
        self.lbl_outdir.grid(row=1, column=0, sticky="w", padx=5)
        self.outdir_entry = tk.Entry(frame_top, width=60, font=FONT_DEFAULT,
                                     bg="#2b2b2b", fg=DARK_FG, insertbackground=DARK_FG)
        self.outdir_entry.grid(row=1, column=1, padx=5, pady=2)
        self.btn_choose = tk.Button(frame_top, text=LANG[self.lang]["choose_dir"],
                                    font=FONT_DEFAULT, bg="#6c757d", fg="white",
                                    command=self.choose_dir)
        self.btn_choose.grid(row=1, column=2, padx=5)

        button_frame = tk.Frame(frame_top, bg=DARK_BG)
        button_frame.grid(row=0, column=3, rowspan=3, padx=5, sticky="n")
        self.btn_add_book = tk.Button(button_frame, text=LANG[self.lang]["add_book"],
                                      font=FONT_DEFAULT, bg="#007bff", fg="white",
                                      width=20, command=self.add_book)
        self.btn_add_book.pack(pady=2)
        self.btn_delete_book = tk.Button(button_frame, text=LANG[self.lang]["delete_book"],
                                         font=FONT_DEFAULT, bg="#dc3545", fg="white",
                                         width=20, command=self.delete_book)
        self.btn_delete_book.pack(pady=2)
        self.btn_change_pages = tk.Button(button_frame, text=LANG[self.lang]["change_pages"],
                                          font=FONT_DEFAULT, bg="#ffc107", fg="black",
                                          width=20, command=self.change_pages)
        self.btn_change_pages.pack(pady=2)
        master.bind("<Delete>", lambda e: self.delete_book())

        self.lbl_pages = tk.Label(frame_top, text=LANG[self.lang]["pages"],
                                  font=FONT_DEFAULT, bg=DARK_BG, fg=DARK_FG)
        self.lbl_pages.grid(row=2, column=0, sticky="w", padx=5)
        self.pages_entry = tk.Entry(frame_top, width=30, font=FONT_DEFAULT,
                                    bg="#2b2b2b", fg=DARK_FG, insertbackground=DARK_FG)
        self.pages_entry.grid(row=2, column=1, sticky="w", padx=5, pady=2)
        self.lbl_pages_hint = tk.Label(frame_top, text=LANG[self.lang]["pages_hint"],
                                       font=("Calibri", 10, "italic"), bg=DARK_BG, fg="#aaaaaa")
        self.lbl_pages_hint.grid(row=3, column=1, sticky="w", padx=5)

        btn_dl_frame = tk.Frame(master, bg=DARK_BG)
        btn_dl_frame.pack(pady=10)
        button_size = {"width": 20, "height": 2}
        self.btn_download = tk.Button(btn_dl_frame, text=LANG[self.lang]["download"],
                                      font=FONT_DEFAULT, bg="#28a745", fg="white",
                                      **button_size, command=self.start_books)
        self.btn_download.pack(side="left", padx=5)
        self.btn_stop = tk.Button(btn_dl_frame, text=LANG[self.lang]["stop"],
                                  font=FONT_DEFAULT, bg="#dc3545", fg="white",
                                  **button_size, command=self.stop_download)
        self.btn_stop.pack(side="left", padx=5)
        self.btn_reset = tk.Button(btn_dl_frame, text=LANG[self.lang]["reset"],
                                   font=FONT_DEFAULT, bg="#007bff", fg="white",
                                   **button_size, command=self.reset_books)
        self.btn_reset.pack(side="left", padx=5)

        save_load_frame = tk.Frame(master, bg=DARK_BG)
        save_load_frame.pack(pady=5)
        self.btn_save_list = tk.Button(save_load_frame, text=LANG[self.lang]["save_list"],
                                       font=FONT_DEFAULT, bg="#6c757d", fg="white",
                                       width=20, command=self.save_list)
        self.btn_save_list.pack(side="left", padx=5)
        self.btn_load_list = tk.Button(save_load_frame, text=LANG[self.lang]["load_list"],
                                       font=FONT_DEFAULT, bg="#6c757d", fg="white",
                                       width=20, command=self.load_list)
        self.btn_load_list.pack(side="left", padx=5)
        self.btn_export_pdf = tk.Button(save_load_frame, text=LANG[self.lang]["export_pdf"],
                                        font=FONT_DEFAULT, bg="#17a2b8", fg="white",
                                        width=20, command=self.export_pdf)
        self.btn_export_pdf.pack(side="left", padx=5)

        self.lbl_waiting = tk.Label(master, text=LANG[self.lang]["waiting_list"],
                                    font=FONT_DEFAULT, bg=DARK_BG, fg=DARK_FG)
        self.lbl_waiting.pack(anchor="w", padx=5)
        frame_list = tk.Frame(master, bg=DARK_BG)
        frame_list.pack(fill="both", expand=True, padx=5, pady=5)

        columns = ("book", "pages", "status")
        self.tree = ttk.Treeview(frame_list, columns=columns, show="headings", selectmode="extended")
        self.tree.heading("book", text=LANG[self.lang]["col_book"])
        self.tree.heading("pages", text=LANG[self.lang]["col_pages"])
        self.tree.heading("status", text=LANG[self.lang]["col_status"])
        self.tree.column("book", width=600)
        self.tree.column("pages", width=100, anchor="center")
        self.tree.column("status", width=80, anchor="center")
        self.tree.pack(side="left", fill="both", expand=True)

        scrollbar = tk.Scrollbar(frame_list, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.tree.config(yscrollcommand=scrollbar.set)

        self.tree.bind("<Double-1>", self.open_book_url)

        self.lbl_progress = tk.Label(master, text=LANG[self.lang]["global_progress"],
                                     font=FONT_DEFAULT, bg=DARK_BG, fg=DARK_FG)
        self.lbl_progress.pack(anchor="w", padx=5)
        self.global_progress_frame = tk.Frame(master, bg=DARK_BG)
        self.global_progress_frame.pack(fill="x", padx=5)
        self.global_progress = ttk.Progressbar(self.global_progress_frame, length=1000, mode="determinate")
        self.global_progress.pack(side="left", fill="x", expand=True)
        self.global_progress_label = tk.Label(self.global_progress_frame, text="0%",
                                              font=FONT_DEFAULT, bg=DARK_BG, fg=DARK_FG)
        self.global_progress_label.pack(side="left", padx=5)

        self.log_frame = tk.Frame(master, bg=DARK_BG)
        self.log_text = tk.Text(self.log_frame, height=12, font=("Consolas", 10),
                                bg="#111111", fg="#dddddd", insertbackground=DARK_FG)
        self.log_text.pack(fill="both", expand=True)

    def open_home(self):
        webbrowser.open("https://www.portafontium.eu/searching")

    def open_book_url(self, event):
        item = self.tree.identify_row(event.y)
        if not item:
            return
        values = self.tree.item(item, "values")
        if values and values[0]:
            webbrowser.open(values[0])

    def choose_dir(self):
        d = filedialog.askdirectory()
        if d:
            self.outdir_entry.delete(0, "end")
            self.outdir_entry.insert(0, d)

    def toggle_log(self):
        if self.log_open:
            self.log_frame.pack_forget()
            self.btn_log_toggle.config(text=LANG[self.lang]["log_open"])
        else:
            self.log_frame.pack(fill="both", expand=True, padx=8, pady=4)
            self.btn_log_toggle.config(text=LANG[self.lang]["log_close"])
        self.log_open = not self.log_open

    def log(self, msg):
        line = f"{datetime.now().strftime('%H:%M:%S')} {msg}"
        self.log_lines.append(line)
        self.log_text.insert("end", line + "\n")
        self.log_text.see("end")

        # globales Logfile im Zielordner (optional)
        if self.save_log_var.get() and self.books:
            outdir = self.books[0].get("outdir", "")
            if outdir and os.path.isdir(outdir):
                logfile = os.path.join(outdir, "download_log.txt")
                try:
                    with open(logfile, "a", encoding="utf-8") as f:
                        f.write(line + "\n")
                except Exception:
                    pass

    def add_book(self):
        url = self.url_entry.get().strip()
        outdir = self.outdir_entry.get().strip()
        pages = self.pages_entry.get().strip()
        if not url:
            messagebox.showwarning(LANG[self.lang]["title"], LANG[self.lang]["error_no_url"])
            return
        if not outdir:
            outdir = os.getcwd()
        book = {"url": url, "outdir": outdir, "pages": pages}
        self.books.append(book)
        self.tree.insert("", "end", values=(url, pages, "⏳"))
        self.log(f"[+] Buch hinzugefügt: {url}")

        # Eingabefelder zurücksetzen
        self.url_entry.delete(0, "end")
        self.pages_entry.delete(0, "end")

        # Fokus zurück auf URL-Feld
        self.url_entry.focus_set()

    def delete_book(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning(LANG[self.lang]["title"], LANG[self.lang]["error_no_selection"])
            return
        for item in reversed(sel):
            idx = self.tree.index(item)
            del self.books[idx]
            self.tree.delete(item)
        self.log("[-] Buch gelöscht.")

    def change_pages(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning(LANG[self.lang]["title"], LANG[self.lang]["error_no_selection"])
            return
        item = sel[0]
        idx = self.tree.index(item)
        current_pages = self.books[idx]["pages"]
        pages = simpledialog.askstring(LANG[self.lang]["change_pages"], LANG[self.lang]["pages_hint"],
                                       initialvalue=current_pages)
        if pages is not None:
            self.books[idx]["pages"] = pages
            values = list(self.tree.item(item, "values"))
            values[1] = pages
            self.tree.item(item, values=values)
            self.log(f"[~] Seiten geändert: {self.books[idx]['url']} -> {pages}")

    def reset_books(self):
        self.books.clear()
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.log("[*] Warteliste zurückgesetzt.")

    def save_list(self):
        if not self.books:
            return
        file = filedialog.asksaveasfilename(defaultextension=".json",
                                            filetypes=[("JSON", "*.json")])
        if file:
            with open(file, "w", encoding="utf-8") as f:
                json.dump(self.books, f, indent=2, ensure_ascii=False)
            self.log(f"[💾] Warteliste gespeichert: {file}")

    def load_list(self):
        file = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if file:
            with open(file, "r", encoding="utf-8") as f:
                self.books = json.load(f)
            for item in self.tree.get_children():
                self.tree.delete(item)
            for b in self.books:
                self.tree.insert("", "end", values=(b["url"], b.get("pages", ""), "⏳"))
            self.log(f"[📂] Warteliste geladen: {file}")

    def export_pdf(self):
        if not self.books:
            messagebox.showwarning(LANG[self.lang]["title"], LANG[self.lang]["pdf_error_no_books"])
            return
        if not HAVE_REPORTLAB:
            messagebox.showerror(LANG[self.lang]["title"], LANG[self.lang]["pdf_error_lib"])
            return

        from PIL import Image

        for book in self.books:
            outdir = book.get("outdir", "")
            if not outdir or not os.path.isdir(outdir):
                continue

            for root, dirs, files in os.walk(outdir):
                images = sorted([f for f in files if f.lower().endswith(".jpg")])
                if not images:
                    continue

                pdf_path = os.path.join(root, os.path.basename(root) + ".pdf")
                c = canvas.Canvas(pdf_path, pagesize=A4)
                pdf_w, pdf_h = A4

                for img in images:
                    img_path = os.path.join(root, img)
                    try:
                        with Image.open(img_path) as im:
                            img_w, img_h = im.size

                            # Verhältnis bestimmen und beibehalten
                            scale = min(pdf_w / img_w, pdf_h / img_h)
                            new_w = img_w * scale
                            new_h = img_h * scale

                            x = (pdf_w - new_w) / 2
                            y = (pdf_h - new_h) / 2

                            c.drawImage(img_path, x, y, width=new_w, height=new_h, preserveAspectRatio=True)
                            c.showPage()

                    except Exception as e:
                        self.log(f"[!] PDF Fehler bei {img}: {e}")

                c.save()
                self.log(f"[📄] PDF exportiert: {pdf_path}")

        messagebox.showinfo(LANG[self.lang]["title"], LANG[self.lang]["pdf_saved"])

    def start_books(self):
        if not self.books:
            messagebox.showwarning(LANG[self.lang]["title"], LANG[self.lang]["error_no_book"])
            return
        self.global_progress["value"] = 0
        self.global_progress_label.config(text="0%")
        self.stop_flag = False
        threading.Thread(target=self.run_books_thread, daemon=True).start()

    def stop_download(self):
        self.stop_flag = True

    def update_progress(self, idx, value):
        if idx == "global":
            self.global_progress["value"] = value
            self.global_progress_label.config(text=f"{int(value)}%")
        else:
            try:
                item = self.tree.get_children()[idx]
            except Exception:
                return
            values = list(self.tree.item(item, "values"))
            values[2] = value
            self.tree.item(item, values=values)

    def run_books_thread(self):
        downloader = Downloader(
            self.books,
            log_callback=self.log,
            progress_callback=self.update_progress,
            stop_flag=lambda: self.stop_flag,
            save_metadata=self.save_log_var.get()
        )
        downloader.run()

    def change_language(self, _=None):
        self.lang = self.lang_var.get()
        L = LANG[self.lang]
        self.master.title(L["title"])
        self.btn_add_book.config(text=L["add_book"])
        self.btn_delete_book.config(text=L["delete_book"])
        self.btn_change_pages.config(text=L["change_pages"])
        self.btn_download.config(text=L["download"])
        self.btn_stop.config(text=L["stop"])
        self.btn_reset.config(text=L["reset"])
        self.btn_choose.config(text=L["choose_dir"])
        self.btn_home.config(text=L["home"])
        self.btn_log_toggle.config(text=L["log_open"] if not self.log_open else L["log_close"])
        self.btn_save_list.config(text=L["save_list"])
        self.btn_load_list.config(text=L["load_list"])
        self.btn_export_pdf.config(text=L["export_pdf"])
        self.chk_save_log.config(text=L["save_log"])
        self.lbl_url.config(text=L["book_url"])
        self.lbl_outdir.config(text=L["target_dir"])
        self.lbl_pages.config(text=L["pages"])
        self.lbl_pages_hint.config(text=L["pages_hint"])
        self.lbl_waiting.config(text=L["waiting_list"])
        self.lbl_progress.config(text=L["global_progress"])
        self.tree.heading("book", text=L["col_book"])
        self.tree.heading("pages", text=L["col_pages"])
        self.tree.heading("status", text=L["col_status"])


if __name__ == "__main__":
    root = tk.Tk()
    app = DownloaderGUI(root)
    root.mainloop()
