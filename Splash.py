import tkinter as tk
import math
import subprocess
import sys
import os
import threading
import time

try:
    from PIL import Image, ImageTk, ImageEnhance
    PIL_OK = True
except:
    PIL_OK = False

W, H = 700, 420
BG   = "#FFFFFF"

ROUGE      = "#CC0000"
BLEU       = "#1E3A8A"
GRIS_CLAIR = "#DDDDDD"
GRIS_F     = "#888888"

def lerp(a, b, t):
    return a + (b - a) * max(0, min(1, t))

def lerp_color(c1, c2, t):
    def h(s):
        s = s.lstrip('#')
        return tuple(int(s[i:i+2], 16) for i in (0, 2, 4))
    r1,g1,b1 = h(c1); r2,g2,b2 = h(c2)
    return f'#{int(lerp(r1,r2,t)):02x}{int(lerp(g1,g2,t)):02x}{int(lerp(b1,b2,t)):02x}'


class Splash:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("TradAIx")
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f"{W}x{H}+{(sw-W)//2}+{(sh-H)//2}")
        self.root.resizable(False, False)
        self.root.overrideredirect(True)

        self.c = tk.Canvas(self.root, width=W, height=H, bg=BG, highlightthickness=0)
        self.c.pack()

        self.frame        = 0
        self.running      = True
        self.letters      = ["T","r","a","d","A","I","x"]
        self.letter_items = []
        self.letter_shown = 0
        self.phase        = "appear"
        self.color_idx    = 0
        self.color_prog   = 0.0
        self.update_done  = False
        self.update_msg   = "Vérification des mises à jour..."

        self._build()

        # Lancer la vérification MAJ en arrière-plan
        threading.Thread(target=self._verifier_maj, daemon=True).start()

        self._loop()
        self.root.mainloop()

    # ─────────────────────────────────────────
    def _build(self):
        c = self.c

        # Icône en fond
        dossier   = os.path.dirname(os.path.abspath(__file__))
        self.logo_photo = None
        for nom in ["TradAIx.ico", "logo_tradaix_mascotte.png"]:
            chemin = os.path.join(dossier, nom)
            if PIL_OK and os.path.exists(chemin):
                try:
                    img = Image.open(chemin).convert("RGBA")
                    r, g, b, a = img.split()
                    a = ImageEnhance.Brightness(a).enhance(0.10)
                    img.putalpha(a)
                    img = img.resize((300, 300), Image.LANCZOS)
                    bg_img = Image.new("RGBA", img.size, (255,255,255,255))
                    bg_img.paste(img, mask=img.split()[3])
                    self.logo_photo = ImageTk.PhotoImage(bg_img.convert("RGB"))
                    c.create_image(W//2, H//2 - 20, image=self.logo_photo, anchor="center")
                    break
                except:
                    pass

        # Lettres
        font_size = 80
        total_w   = len(self.letters) * 62
        start_x   = (W - total_w) // 2
        self.letter_x = []
        self.letter_y = H // 2 - 15
        init_colors   = [GRIS_CLAIR]*4 + [GRIS_F, GRIS_F] + [GRIS_CLAIR]

        for i, ch in enumerate(self.letters):
            xp = start_x + i * 62
            self.letter_x.append(xp)
            sid = c.create_text(xp+3, self.letter_y+3, text=ch,
                                font=("Impact", font_size, "bold"),
                                fill=GRIS_CLAIR, anchor="w", state="hidden")
            lid = c.create_text(xp, self.letter_y, text=ch,
                                font=("Impact", font_size, "bold"),
                                fill=init_colors[i], anchor="w", state="hidden")
            self.letter_items.append((sid, lid))

        self.sub_id  = c.create_text(W//2, self.letter_y+62,
                                     text="INTELLIGENCE COLLABORATIVE",
                                     font=("Courier", 12, "bold"),
                                     fill=GRIS_CLAIR, state="hidden")
        self.line_id = c.create_line(W//2-160, self.letter_y+75,
                                     W//2+160, self.letter_y+75,
                                     fill=GRIS_CLAIR, width=1, state="hidden")

        # Barre de progression
        self.bar_bg  = c.create_rectangle(W//2-140, H-50, W//2+140, H-36,
                                          fill="#F0F0F0", outline=GRIS_CLAIR, width=1)
        self.bar_fg  = c.create_rectangle(W//2-140, H-50, W//2-140, H-36,
                                          fill=ROUGE, outline="")
        self.bar_txt = c.create_text(W//2, H-24, text="Initialisation...",
                                     font=("Courier", 9), fill=GRIS_F)

        # Version
        self.ver_txt = c.create_text(W//2, H-10, text="",
                                     font=("Courier", 8), fill=GRIS_CLAIR)

        # Copyright
        c.create_text(10, H-5, text="TradAIx © 2026",
                      fill=GRIS_CLAIR, font=("Courier", 8), anchor="w")

    # ─────────────────────────────────────────
    def _verifier_maj(self):
        """Vérification MAJ en arrière-plan."""
        try:
            dossier = os.path.dirname(os.path.abspath(__file__))
            sys.path.insert(0, dossier)
            from updater import verifier_et_mettre_a_jour, lire_version_locale

            version = lire_version_locale()
            self.root.after(0, lambda: self.c.itemconfig(
                self.ver_txt, text=f"v{version}"))

            def log_cb(msg):
                self.update_msg = msg

            result = verifier_et_mettre_a_jour(callback=log_cb)

            if result["maj"]:
                self.update_msg = f"✓ Mise à jour v{result['version']} appliquée !"
            else:
                self.update_msg = result["message"]
        except Exception as e:
            self.update_msg = "Prêt."
        finally:
            self.update_done = True

    # ─────────────────────────────────────────
    def _update_bar(self, prog, texte):
        x0   = W//2 - 140
        x1   = W//2 + 140
        fill = x0 + int((x1-x0) * max(0, min(1, prog)))
        self.c.coords(self.bar_fg, x0, H-50, fill, H-36)
        self.c.itemconfig(self.bar_txt, text=texte[:60])

    # ─────────────────────────────────────────
    def _loop(self):
        if not self.running:
            return

        c = self.c
        f = self.frame

        # Afficher le message de MAJ dans la barre
        if self.update_msg:
            self.c.itemconfig(self.bar_txt, text=self.update_msg[:60])

        # PHASE 1 : apparition lettres
        if self.phase == "appear":
            interval = 10
            idx = (f - 5) // interval
            while self.letter_shown <= idx and self.letter_shown < len(self.letter_items):
                sid, lid = self.letter_items[self.letter_shown]
                c.itemconfig(sid, state="normal")
                c.itemconfig(lid, state="normal")
                self.letter_shown += 1

            prog = min(self.letter_shown / len(self.letters) * 0.35, 0.35)
            self._update_bar(prog, self.update_msg or "Initialisation...")

            if self.letter_shown >= len(self.letter_items):
                c.itemconfig(self.sub_id,  state="normal")
                c.itemconfig(self.line_id, state="normal")
                if f > 5 + interval * len(self.letters) + 20:
                    self.phase      = "color"
                    self.color_idx  = 0
                    self.color_prog = 0.0

        # PHASE 2 : coloration
        elif self.phase == "color":
            idx = self.color_idx
            if idx < len(self.letters):
                self.color_prog = min(self.color_prog + 0.04, 1.0)
                t   = self.color_prog
                sid, lid = self.letter_items[idx]
                cible = BLEU if self.letters[idx] in ("A","I") else ROUGE
                init  = GRIS_F if self.letters[idx] in ("A","I") else GRIS_CLAIR
                c.itemconfig(lid, fill=lerp_color(init, cible, t))
                c.itemconfig(sid, fill=lerp_color(GRIS_CLAIR, "#AA0000", t))
                global_t = (idx + t) / len(self.letters)
                c.itemconfig(self.sub_id,  fill=lerp_color(GRIS_CLAIR, ROUGE, global_t))
                c.itemconfig(self.line_id, fill=lerp_color(GRIS_CLAIR, ROUGE, global_t))
                prog = 0.35 + global_t * 0.50
                self._update_bar(prog, self.update_msg or "Chargement TradAIx...")
                if self.color_prog >= 1.0:
                    self.color_idx  += 1
                    self.color_prog  = 0.0
            else:
                # Attendre que la MAJ soit terminée
                if self.update_done:
                    self._update_bar(1.0, "Prêt !")
                    self.phase   = "done"
                    self.running = False
                    self._lancer_app()
                    return
                else:
                    self._update_bar(0.90, self.update_msg or "Finalisation...")

        self.frame += 1
        self.root.after(16, self._loop)

    # ─────────────────────────────────────────
    def _lancer_app(self):
        dossier = os.path.dirname(os.path.abspath(__file__))
        def run():
            time.sleep(0.4)
            subprocess.Popen(
                [sys.executable, os.path.join(dossier, "launcher_exe.py")],
                cwd=dossier
            )
            self.root.after(600, self.root.destroy)
        threading.Thread(target=run, daemon=True).start()


if __name__ == "__main__":
    Splash()
