import os
import json
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, parse_qs, urlencode
import webbrowser
from datetime import datetime

DEFAULT_HEADERS = {"User-Agent": "portafontium-downloader/GUI"}
FONT_DEFAULT = ("Calibri", 12)

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
        "save_log": "📄 Log speichern"
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
        "save_log": "📄 Save log"
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
        "save_log": "📄 Uložit log"
    }
}

# --- Hilfsfunktionen ---
def fetch_html(url, session):
    r = session.get(url, timeout=20)
    r.raise_for_status()
    return r.text

def find_iip_links(html, base_url):
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for tag in soup.find_all(["a", "img"], href=True) + soup.find_all("img", src=True):
        attr = tag.get("href") or tag.get("src")
        if not attr:
            continue
        if "iipsrv" in attr or "fcgi-bin" in attr:
            links.append(urljoin(base_url, attr))
    return list(dict.fromkeys(links))

def build_download_url(iip_url):
    parsed = urlparse(iip_url)
    qs = parse_qs(parsed.query)
    fif = qs.get("FIF", [None])[0]
    if not fif:
        return iip_url
    base = parsed.scheme + "://" + parsed.netloc + parsed.path
    params = {"FIF": fif, "cvt": "jpeg", "Q": "90"}
    return base + "?" + urlencode(params, safe="/:,")

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

# --- Downloader ---
class Downloader:
    def __init__(self, books, log_callback=None, progress_callback=None, stop_flag=lambda: False):
        self.books = books
        self.log = log_callback or (lambda msg: None)
        self.progress_update = progress_callback or (lambda idx, val: None)
        self.stop_flag = stop_flag
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)

    def parse_pages(self, pages_str, total):
        if not pages_str.strip():
            return list(range(1, total + 1))
        pages_to_download = []
        for part in pages_str.split(","):
            if "-" in part:
                try:
                    a, b = map(int, part.split("-"))
                    pages_to_download.extend(i for i in range(a, b + 1) if 1 <= i <= total)
                except:
                    pass
            else:
                try:
                    i = int(part)
                    if 1 <= i <= total:
                        pages_to_download.append(i)
                except:
                    pass
        return sorted(set(pages_to_download))

    def extract_book_id(self, url):
        """Extrahiert die ID aus der URL (z.B. ?id=12345 oder &id=678)."""
        parsed = urlparse(url)
        qs = parse_qs(parsed.query)
        book_id = qs.get("id", [None])[0]
        if not book_id:
            # Fallback: Letzter URL-Teil falls keine ID-Query
            book_id = os.path.basename(parsed.path).strip("/") or "unknown"
        return book_id

    def run(self):
        total_books = len(self.books)
        books_done = 0

        for idx, book in enumerate(self.books):
            if self.stop_flag():
                self.log("[*] Abgebrochen.")
                self.progress_update(idx, "❌")
                continue

            try:
                html = fetch_html(book["url"], self.session)
                links = find_iip_links(html, book["url"])
            except Exception:
                links = []

            if not links:
                self.log(f"[!] Keine Seiten gefunden für {book['url']}")
                self.progress_update(idx, "⚠️")
                books_done += 1
                self.progress_update("global", books_done / total_books * 100)
                continue

            os.makedirs(book["outdir"], exist_ok=True)
            pages_to_download = self.parse_pages(book.get("pages",""), len(links))
            errors = 0

            # NEU: Buch-ID aus der URL extrahieren
            book_id = self.extract_book_id(book["url"])

            for i in pages_to_download:
                if self.stop_flag():
                    self.log("[*] Abgebrochen.")
                    errors += 1
                    break
                link = links[i-1]
                # >>> Angepasster Dateiname
                fname = f"{book_id}_page_{i:04d}.jpg"
                outpath = os.path.join(book["outdir"], fname)
                dl_url = build_download_url(link)
                self.log(f"Lade {fname}")
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



        # Top Home + Sprache + Log Toggle
        top_frame = tk.Frame(master)
        top_frame.pack(fill="x", pady=5)

        self.btn_home = tk.Button(top_frame, text=LANG[self.lang]["home"], font=FONT_DEFAULT, bg="#1E90FF", fg="white", command=self.open_home)
        self.btn_home.pack(side="left", padx=5)

        self.lang_var = tk.StringVar(value=self.lang)
        for l in ["de","en","cs"]:
            tk.Radiobutton(top_frame, text=l.upper(), variable=self.lang_var, value=l, command=self.change_language).pack(side="left")

        self.btn_log_toggle = tk.Button(top_frame, text=LANG[self.lang]["log_open"], font=FONT_DEFAULT, bg="#6c757d", fg="white", command=self.toggle_log)
        self.btn_log_toggle.pack(side="right", padx=5)

        self.save_log_var = tk.BooleanVar(value=False)
        self.chk_save_log = tk.Checkbutton(top_frame, text=LANG[self.lang]["save_log"], variable=self.save_log_var, font=FONT_DEFAULT)
        self.chk_save_log.pack(side="right", padx=5)

        # Eingaben
        frame_top = tk.Frame(master)
        frame_top.pack(fill="x", padx=10, pady=5)

        self.lbl_url = tk.Label(frame_top, text=LANG[self.lang]["book_url"], font=FONT_DEFAULT)
        self.lbl_url.grid(row=0, column=0, sticky="w", padx=5)
        self.url_entry = tk.Entry(frame_top, width=60, font=FONT_DEFAULT)
        self.url_entry.grid(row=0, column=1, padx=5, pady=2)

        self.lbl_outdir = tk.Label(frame_top, text=LANG[self.lang]["target_dir"], font=FONT_DEFAULT)
        self.lbl_outdir.grid(row=1, column=0, sticky="w", padx=5)
        self.outdir_entry = tk.Entry(frame_top, width=60, font=FONT_DEFAULT)
        self.outdir_entry.grid(row=1, column=1, padx=5, pady=2)
        self.btn_choose = tk.Button(frame_top, text=LANG[self.lang]["choose_dir"], font=FONT_DEFAULT, bg="#6c757d", fg="white", command=self.choose_dir)
        self.btn_choose.grid(row=1, column=2, padx=5)

        # Buttons rechts untereinander
        button_frame = tk.Frame(frame_top)
        button_frame.grid(row=0, column=3, rowspan=3, padx=5, sticky="n")
        self.btn_add_book = tk.Button(button_frame, text=LANG[self.lang]["add_book"], font=FONT_DEFAULT, bg="#007bff", fg="white", width=20, command=self.add_book)
        self.btn_add_book.pack(pady=2)
        self.btn_delete_book = tk.Button(button_frame, text=LANG[self.lang]["delete_book"], font=FONT_DEFAULT, bg="#dc3545", fg="white", width=20, command=self.delete_book)
        self.btn_delete_book.pack(pady=2)
        self.btn_change_pages = tk.Button(button_frame, text=LANG[self.lang]["change_pages"], font=FONT_DEFAULT, bg="#ffc107", fg="black", width=20, command=self.change_pages)
        self.btn_change_pages.pack(pady=2)
        master.bind("<Delete>", lambda e: self.delete_book())

        self.lbl_pages = tk.Label(frame_top, text=LANG[self.lang]["pages"], font=FONT_DEFAULT)
        self.lbl_pages.grid(row=2, column=0, sticky="w", padx=5)
        self.pages_entry = tk.Entry(frame_top, width=30, font=FONT_DEFAULT)
        self.pages_entry.grid(row=2, column=1, sticky="w", padx=5, pady=2)
        self.lbl_pages_hint = tk.Label(frame_top, text=LANG[self.lang]["pages_hint"], font=("Calibri", 10, "italic"))
        self.lbl_pages_hint.grid(row=3, column=1, sticky="w", padx=5)

        # Download Buttons
        btn_dl_frame = tk.Frame(master)
        btn_dl_frame.pack(pady=10)
        button_size = {"width": 20, "height": 2}
        self.btn_download = tk.Button(btn_dl_frame, text=LANG[self.lang]["download"], font=FONT_DEFAULT, bg="#28a745", fg="white", **button_size, command=self.start_books)
        self.btn_download.pack(side="left", padx=5)
        self.btn_stop = tk.Button(btn_dl_frame, text=LANG[self.lang]["stop"], font=FONT_DEFAULT, bg="#dc3545", fg="white", **button_size, command=self.stop_download)
        self.btn_stop.pack(side="left", padx=5)
        self.btn_reset = tk.Button(btn_dl_frame, text=LANG[self.lang]["reset"], font=FONT_DEFAULT, bg="#007bff", fg="white", **button_size, command=self.reset_books)
        self.btn_reset.pack(side="left", padx=5)

        # Save/Load Buttons zentriert
        save_load_frame = tk.Frame(master)
        save_load_frame.pack(pady=5)
        self.btn_save_list = tk.Button(save_load_frame, text=LANG[self.lang]["save_list"], font=FONT_DEFAULT, bg="#6c757d", fg="white", width=20, command=self.save_list)
        self.btn_save_list.pack(side="left", padx=5)
        self.btn_load_list = tk.Button(save_load_frame, text=LANG[self.lang]["load_list"], font=FONT_DEFAULT, bg="#6c757d", fg="white", width=20, command=self.load_list)
        self.btn_load_list.pack(side="left", padx=5)

        # Warteliste als Tabelle
        self.lbl_waiting = tk.Label(master, text=LANG[self.lang]["waiting_list"], font=FONT_DEFAULT)
        self.lbl_waiting.pack(anchor="w", padx=5)
        frame_list = tk.Frame(master)
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

        # Progress
        self.lbl_progress = tk.Label(master, text=LANG[self.lang]["global_progress"], font=FONT_DEFAULT)
        self.lbl_progress.pack(anchor="w", padx=5)
        self.global_progress_frame = tk.Frame(master)
        self.global_progress_frame.pack(fill="x", padx=5)
        self.global_progress = ttk.Progressbar(self.global_progress_frame, length=1000, mode="determinate")
        self.global_progress.pack(side="left", fill="x", expand=True)
        self.global_progress_label = tk.Label(self.global_progress_frame, text="0%", font=FONT_DEFAULT)
        self.global_progress_label.pack(side="left", padx=5)

        # Log
        self.log_frame = tk.Frame(master)
        self.log_text = tk.Text(self.log_frame, height=12, font=("Consolas", 10))
        self.log_text.pack(fill="both", expand=True)

        # --- Methoden ---

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
        translations = {
            "Abgebrochen": {"de": "Abgebrochen", "en": "Cancelled", "cs": "Zrušeno"},
            "Keine Seiten gefunden für": {"de": "Keine Seiten gefunden für", "en": "No pages found for",
                                          "cs": "Žádné stránky nalezeny pro"},
            "Buch hinzugefügt": {"de": "Buch hinzugefügt", "en": "Book added", "cs": "Kniha přidána"},
            "Buch gelöscht": {"de": "Buch gelöscht", "en": "Book deleted", "cs": "Kniha smazána"},
            "Seiten geändert": {"de": "Seiten geändert", "en": "Pages changed", "cs": "Stránky změněny"},
            "Alle Bücher fertig": {"de": "Alle Bücher fertig", "en": "All books finished",
                                   "cs": "Všechny knihy dokončeny"},
            "Warteliste gespeichert": {"de": "Warteliste gespeichert", "en": "Waiting List saved",
                                       "cs": "Seznam uložen"},
            "Warteliste geladen": {"de": "Warteliste geladen", "en": "Waiting List loaded", "cs": "Seznam načten"}
        }

        for key, val in translations.items():
            if key in msg:
                msg = msg.replace(key, val[self.lang])

        line = f"{datetime.now().strftime('%H:%M:%S')} {msg}"
        self.log_lines.append(line)
        self.log_text.insert("end", line + "\n")
        self.log_text.see("end")

        if self.save_log_var.get() and self.books:
            outdir = self.books[0].get("outdir", "")
            if outdir and os.path.isdir(outdir):
                logfile = os.path.join(outdir, "download_log.txt")
                with open(logfile, "a", encoding="utf-8") as f:
                    f.write(line + "\n")

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

    def delete_book(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning(LANG[self.lang]["title"], LANG[self.lang]["error_no_selection"])
            return
        for item in sel:
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
        prefix = {
            "de": "Warteliste",
            "en": "Waiting List",
            "cs": "Seznam"
        }[self.lang]
        date_str = datetime.now().strftime("%Y-%m-%d")
        default_name = f"{prefix}+{date_str}.json"
        file = filedialog.asksaveasfilename(defaultextension=".json", initialfile=default_name,
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
            item = self.tree.get_children()[idx]
            values = list(self.tree.item(item, "values"))
            values[2] = value
            self.tree.item(item, values=values)

    def run_books_thread(self):
        downloader = Downloader(self.books, log_callback=self.log, progress_callback=self.update_progress,
                                stop_flag=lambda: self.stop_flag)
        downloader.run()

    def change_language(self, _=None):
        self.lang = self.lang_var.get()
        self.btn_add_book.config(text=LANG[self.lang]["add_book"])
        self.btn_delete_book.config(text=LANG[self.lang]["delete_book"])
        self.btn_change_pages.config(text=LANG[self.lang]["change_pages"])
        self.btn_download.config(text=LANG[self.lang]["download"])
        self.btn_stop.config(text=LANG[self.lang]["stop"])
        self.btn_reset.config(text=LANG[self.lang]["reset"])
        self.btn_choose.config(text=LANG[self.lang]["choose_dir"])
        self.btn_home.config(text=LANG[self.lang]["home"])
        self.btn_log_toggle.config(
            text=LANG[self.lang]["log_open"] if not self.log_open else LANG[self.lang]["log_close"])
        self.btn_save_list.config(text=LANG[self.lang]["save_list"])
        self.btn_load_list.config(text=LANG[self.lang]["load_list"])
        self.chk_save_log.config(text=LANG[self.lang]["save_log"])
        self.lbl_url.config(text=LANG[self.lang]["book_url"])
        self.lbl_outdir.config(text=LANG[self.lang]["target_dir"])
        self.lbl_pages.config(text=LANG[self.lang]["pages"])
        self.lbl_pages_hint.config(text=LANG[self.lang]["pages_hint"])
        self.lbl_waiting.config(text=LANG[self.lang]["waiting_list"])
        self.lbl_progress.config(text=LANG[self.lang]["global_progress"])
        self.tree.heading("book", text=LANG[self.lang]["col_book"])
        self.tree.heading("pages", text=LANG[self.lang]["col_pages"])
        self.tree.heading("status", text=LANG[self.lang]["col_status"])
        self.master.title(LANG[self.lang]["title"])

if __name__ == "__main__":
    root = tk.Tk()
    app = DownloaderGUI(root)
    root.mainloop()
