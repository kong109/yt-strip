"""YT Strip GUI — tkinter interface for downloading YouTube audio."""

import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from urllib.parse import urlparse, parse_qs

from . import downloader


class App:
    """Main application window."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Liisa is a pirate")
        self.root.geometry("900x680")
        self.root.minsize(780, 520)

        # State
        self.info = None
        self.track_widgets = []
        self._downloading = False
        self._cancel = False

        self._build_ui()
        self._check_ffmpeg()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        style = ttk.Style()
        try:
            style.theme_use('aqua' if sys.platform == 'darwin' else 'clam')
        except tk.TclError:
            pass

        main = ttk.Frame(self.root, padding=12)
        main.pack(fill=tk.BOTH, expand=True)

        # --- URL ---
        url_frame = ttk.LabelFrame(main, text="YouTube URL", padding=8)
        url_frame.pack(fill=tk.X, pady=(0, 8))

        self.url_var = tk.StringVar()
        url_entry = ttk.Entry(url_frame, textvariable=self.url_var)
        url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        url_entry.bind("<Return>", lambda _: self._on_fetch())

        self.fetch_btn = ttk.Button(url_frame, text="Fetch", command=self._on_fetch)
        self.fetch_btn.pack(side=tk.RIGHT)

        # --- Output directory ---
        out_frame = ttk.LabelFrame(main, text="Save To", padding=8)
        out_frame.pack(fill=tk.X, pady=(0, 8))

        default_dir = str(Path.home() / "Music")
        self.output_var = tk.StringVar(value=default_dir)
        ttk.Entry(out_frame, textvariable=self.output_var).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        ttk.Button(out_frame, text="Browse", command=self._on_browse).pack(side=tk.RIGHT)

        # --- Dynamic content area ---
        self.content_frame = ttk.Frame(main)
        self.content_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        self._show_unicorn_splash()

        # --- Progress ---
        progress_frame = ttk.Frame(main)
        progress_frame.pack(fill=tk.X)

        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(
            progress_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, pady=(0, 4))

        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(progress_frame, textvariable=self.status_var).pack(anchor=tk.W)

    # ------------------------------------------------------------------
    # Single-video view
    # ------------------------------------------------------------------

    def _show_unicorn_splash(self):
        """Draw a pirate-unicorn splash in the content area."""
        c = tk.Canvas(self.content_frame, highlightthickness=0, bg='#f0e6ff')
        c.pack(fill=tk.BOTH, expand=True)

        def _draw(event=None):
            c.delete('u')
            w, h = c.winfo_width(), c.winfo_height()
            if w < 10 or h < 10:
                return
            cx, cy = w // 2, h // 2
            s = min(w, h) / 420          # scale factor

            # --- HEAD (front view, rounded) ---
            c.create_oval(cx - 95*s, cy - 75*s, cx + 95*s, cy + 105*s,
                          fill='#f8e8ff', outline='#c890e0', width=2*s, tags='u')

            # --- SNOUT / MUZZLE ---
            c.create_oval(cx - 50*s, cy + 45*s, cx + 50*s, cy + 125*s,
                          fill='#ffe4f0', outline='#c890e0', width=2*s, tags='u')
            # nostrils
            c.create_oval(cx - 16*s, cy + 78*s, cx - 6*s, cy + 90*s,
                          fill='#e0b0c8', outline='', tags='u')
            c.create_oval(cx + 6*s, cy + 78*s, cx + 16*s, cy + 90*s,
                          fill='#e0b0c8', outline='', tags='u')

            # --- SMILE ---
            c.create_arc(cx - 28*s, cy + 55*s, cx + 28*s, cy + 100*s,
                         start=200, extent=140, style=tk.ARC,
                         outline='#c890e0', width=2*s, tags='u')

            # --- HORN (golden, spiraled) ---
            c.create_polygon(cx - 14*s, cy - 72*s,
                             cx,        cy - 175*s,
                             cx + 14*s, cy - 72*s,
                             fill='#ffd700', outline='#daa520', width=2*s,
                             smooth=False, tags='u')
            for i in range(5):
                yy = cy - 82*s - i * 18*s
                c.create_line(cx - 11*s + i*2*s, yy,
                              cx + 11*s - i*2*s, yy,
                              fill='#daa520', width=max(1, 1.2*s), tags='u')

            # --- EARS ---
            # left ear
            c.create_polygon(cx - 60*s, cy - 55*s,
                             cx - 80*s, cy - 115*s,
                             cx - 40*s, cy - 70*s,
                             fill='#ffe4f0', outline='#c890e0', width=2*s, tags='u')
            # right ear
            c.create_polygon(cx + 60*s, cy - 55*s,
                             cx + 80*s, cy - 115*s,
                             cx + 40*s, cy - 70*s,
                             fill='#ffe4f0', outline='#c890e0', width=2*s, tags='u')

            # --- RIGHT EYE (cute, visible) ---
            c.create_oval(cx + 18*s, cy - 30*s, cx + 62*s, cy + 14*s,
                          fill='white', outline='#555', width=2*s, tags='u')
            c.create_oval(cx + 28*s, cy - 18*s, cx + 52*s, cy + 6*s,
                          fill='#7b68ee', outline='#5b48ce', width=1, tags='u')
            c.create_oval(cx + 33*s, cy - 12*s, cx + 47*s, cy + 0*s,
                          fill='black', outline='', tags='u')
            # sparkle
            c.create_oval(cx + 35*s, cy - 22*s, cx + 41*s, cy - 16*s,
                          fill='white', outline='', tags='u')
            c.create_oval(cx + 46*s, cy - 8*s, cx + 50*s, cy - 4*s,
                          fill='white', outline='', tags='u')

            # --- LEFT EYE AREA — EYEPATCH! ---
            c.create_oval(cx - 62*s, cy - 32*s, cx - 14*s, cy + 16*s,
                          fill='#1a1a1a', outline='#000', width=2*s, tags='u')
            # skull on eyepatch
            c.create_oval(cx - 48*s, cy - 18*s, cx - 28*s, cy + 0*s,
                          fill='#ddd', outline='', tags='u')
            c.create_line(cx - 44*s, cy + 0*s, cx - 32*s, cy + 8*s,
                          fill='#ddd', width=2*s, tags='u')
            c.create_line(cx - 44*s, cy + 8*s, cx - 32*s, cy + 0*s,
                          fill='#ddd', width=2*s, tags='u')
            # strap going over/around the head
            c.create_line(cx - 56*s, cy - 20*s,
                          cx - 45*s, cy - 65*s,
                          cx,        cy - 72*s,
                          fill='#1a1a1a', width=3.5*s, smooth=True, tags='u')
            c.create_line(cx - 20*s, cy + 10*s,
                          cx + 15*s, cy + 45*s,
                          cx + 55*s, cy + 30*s,
                          fill='#1a1a1a', width=3.5*s, smooth=True, tags='u')

            # --- MANE (rainbow, flowing to the right) ---
            colors = ['#ff6b6b', '#ff9f43', '#feca57',
                      '#48dbfb', '#7b68ee', '#e056a0']
            for i, clr in enumerate(colors):
                ox = i * 14 * s
                c.create_line(
                    cx + 85*s + ox, cy - 60*s + i*8*s,
                    cx + 120*s + ox, cy - 90*s + i*6*s,
                    cx + 155*s + ox, cy - 40*s + i*10*s,
                    cx + 170*s + ox, cy + 20*s + i*10*s,
                    fill=clr, width=5*s, smooth=True,
                    capstyle=tk.ROUND, tags='u')

            # --- CAPTION ---
            c.create_text(cx, cy + 155*s,
                          text="Paste a YouTube URL above and click Fetch",
                          fill='#9070b0', font=("TkDefaultFont", max(10, int(11*s))),
                          tags='u')

        c.bind('<Configure>', _draw)

    def _build_single_view(self, info):
        frame = ttk.LabelFrame(self.content_frame, text="Track Info", padding=12)
        frame.pack(fill=tk.X, pady=(0, 8))

        labels = ["Song Name:", "Album:", "Artist:"]
        self.single_song_var = tk.StringVar(value=info['title'])
        self.single_album_var = tk.StringVar()
        self.single_artist_var = tk.StringVar(value=info.get('uploader', ''))
        vars_ = [self.single_song_var, self.single_album_var, self.single_artist_var]

        for row, (label, var) in enumerate(zip(labels, vars_)):
            ttk.Label(frame, text=label).grid(row=row, column=0, sticky=tk.W, pady=4)
            ttk.Entry(frame, textvariable=var, width=70).grid(
                row=row, column=1, sticky=tk.EW, padx=(8, 0), pady=4)
        frame.columnconfigure(1, weight=1)

        self._add_action_buttons(self._on_download_single)

    # ------------------------------------------------------------------
    # Playlist view
    # ------------------------------------------------------------------

    def _build_playlist_view(self, info):
        entries = info['entries']

        # Bulk metadata
        bulk = ttk.LabelFrame(self.content_frame, text="Apply to All Tracks", padding=8)
        bulk.pack(fill=tk.X, pady=(0, 8))

        row = ttk.Frame(bulk)
        row.pack(fill=tk.X)

        ttk.Label(row, text="Album:").pack(side=tk.LEFT)
        self.bulk_album_var = tk.StringVar(value=info['title'])
        ttk.Entry(row, textvariable=self.bulk_album_var, width=28).pack(
            side=tk.LEFT, padx=(4, 16))

        ttk.Label(row, text="Artist:").pack(side=tk.LEFT)
        self.bulk_artist_var = tk.StringVar()
        ttk.Entry(row, textvariable=self.bulk_artist_var, width=28).pack(
            side=tk.LEFT, padx=(4, 16))

        ttk.Button(row, text="Apply to All", command=self._on_apply_all).pack(side=tk.LEFT)

        # Track list
        list_lf = ttk.LabelFrame(
            self.content_frame,
            text=f"Playlist: \"{info['title']}\"  ({len(entries)} tracks)",
            padding=8)
        list_lf.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        # Column headers
        hdr = ttk.Frame(list_lf)
        hdr.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(hdr, text="#", width=4, anchor=tk.W,
                  font=("TkDefaultFont", 10, "bold")).pack(side=tk.LEFT)
        ttk.Label(hdr, text="Song Name", width=32, anchor=tk.W,
                  font=("TkDefaultFont", 10, "bold")).pack(side=tk.LEFT, padx=(4, 0))
        ttk.Label(hdr, text="Album", width=22, anchor=tk.W,
                  font=("TkDefaultFont", 10, "bold")).pack(side=tk.LEFT, padx=(4, 0))
        ttk.Label(hdr, text="Artist", width=22, anchor=tk.W,
                  font=("TkDefaultFont", 10, "bold")).pack(side=tk.LEFT, padx=(4, 0))

        # Scrollable canvas
        canvas_box = ttk.Frame(list_lf)
        canvas_box.pack(fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(canvas_box, highlightthickness=0)
        vsb = ttk.Scrollbar(canvas_box, orient=tk.VERTICAL, command=canvas.yview)

        inner = ttk.Frame(canvas)
        inner.bind("<Configure>",
                   lambda _: canvas.configure(scrollregion=canvas.bbox("all")))

        cwin = canvas.create_window((0, 0), window=inner, anchor=tk.NW)
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(cwin, width=e.width))
        canvas.configure(yscrollcommand=vsb.set)

        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Mousewheel — only while pointer is over the list
        def _mw(event):
            canvas.yview_scroll(
                -event.delta if sys.platform == 'darwin' else int(-event.delta / 120),
                "units")

        canvas.bind("<Enter>", lambda _: canvas.bind_all("<MouseWheel>", _mw))
        canvas.bind("<Leave>", lambda _: canvas.unbind_all("<MouseWheel>"))

        # Build rows
        self.track_widgets = []
        pad = len(str(len(entries)))

        for entry in entries:
            idx = entry['index']
            r = ttk.Frame(inner)
            r.pack(fill=tk.X, pady=1)

            ttk.Label(r, text=str(idx), width=4).pack(side=tk.LEFT)

            song_var = tk.StringVar(value=f"{idx:0{pad}d} - {entry['title']}")
            ttk.Entry(r, textvariable=song_var, width=32).pack(side=tk.LEFT, padx=(4, 0))

            album_var = tk.StringVar(value=info['title'])
            ttk.Entry(r, textvariable=album_var, width=22).pack(side=tk.LEFT, padx=(4, 0))

            artist_var = tk.StringVar()
            ttk.Entry(r, textvariable=artist_var, width=22).pack(side=tk.LEFT, padx=(4, 0))

            self.track_widgets.append({
                'index': idx,
                'url': entry['url'],
                'song_var': song_var,
                'album_var': album_var,
                'artist_var': artist_var,
            })

        self._add_action_buttons(self._on_download_playlist, label="Download All")

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    def _add_action_buttons(self, download_cmd, label="Download"):
        bf = ttk.Frame(self.content_frame)
        bf.pack(fill=tk.X)
        self.download_btn = ttk.Button(bf, text=label, command=download_cmd)
        self.download_btn.pack(side=tk.LEFT)
        self.cancel_btn = ttk.Button(bf, text="Cancel", command=self._on_cancel,
                                     state=tk.DISABLED)
        self.cancel_btn.pack(side=tk.LEFT, padx=(8, 0))

    def _clear_content(self):
        for w in self.content_frame.winfo_children():
            w.destroy()
        self.track_widgets = []

    def _set_downloading(self, active):
        self._downloading = active
        self._cancel = False
        st = tk.DISABLED if active else tk.NORMAL
        cst = tk.NORMAL if active else tk.DISABLED
        self.download_btn.config(state=st)
        self.cancel_btn.config(state=cst)
        self.fetch_btn.config(state=st)

    def _preflight(self):
        if not downloader.get_ffmpeg_path():
            messagebox.showerror(
                "ffmpeg Required",
                "ffmpeg is needed for audio conversion but was not found.\n\n"
                "macOS:    brew install ffmpeg\n"
                "Windows:  winget install ffmpeg\n"
                "Linux:    sudo apt install ffmpeg\n\n"
                "Restart YT Strip after installing.")
            return False
        if not self.output_var.get().strip():
            messagebox.showwarning("No Output Folder", "Please choose an output folder.")
            return False
        return True

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_browse(self):
        d = filedialog.askdirectory(initialdir=self.output_var.get())
        if d:
            self.output_var.set(d)

    def _resolve_url(self, url):
        """If URL has both a video ID and a playlist ID, ask the user which they want."""
        try:
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
        except Exception:
            return url

        has_video = 'v' in params and params['v'][0]
        has_playlist = 'list' in params and params['list'][0]

        if has_video and has_playlist:
            choice = messagebox.askyesnocancel(
                "Video or Playlist?",
                "This URL contains both a single video and a playlist.\n\n"
                "Yes  =  download just this one song\n"
                "No   =  download the entire playlist\n"
                "Cancel  =  go back")
            if choice is None:
                return None          # user cancelled
            if choice:
                return f"https://www.youtube.com/watch?v={params['v'][0]}"
            # else: keep full URL for playlist
        return url

    def _on_fetch(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("No URL", "Please enter a YouTube URL.")
            return

        url = self._resolve_url(url)
        if url is None:
            return

        self.fetch_btn.config(state=tk.DISABLED)
        self.status_var.set("Fetching info...")
        self.progress_var.set(0)

        def _work():
            try:
                info = downloader.fetch_info(url)
                self.root.after(0, lambda: self._show_info(info))
            except Exception as e:
                self.root.after(0, lambda: self._fetch_error(str(e)))

        threading.Thread(target=_work, daemon=True).start()

    def _fetch_error(self, msg):
        self.fetch_btn.config(state=tk.NORMAL)
        self.status_var.set("Fetch failed")
        messagebox.showerror("Fetch Error", f"Could not fetch info:\n\n{msg}")

    def _show_info(self, info):
        self.info = info
        self.fetch_btn.config(state=tk.NORMAL)
        self._clear_content()

        if info['type'] == 'video':
            self._build_single_view(info)
        else:
            self._build_playlist_view(info)

        self.status_var.set("Ready to download")

    def _on_apply_all(self):
        album = self.bulk_album_var.get()
        artist = self.bulk_artist_var.get()
        for tw in self.track_widgets:
            if album:
                tw['album_var'].set(album)
            if artist:
                tw['artist_var'].set(artist)

    def _on_cancel(self):
        self._cancel = True
        self.status_var.set("Cancelling after current track...")

    # ------------------------------------------------------------------
    # Download — single video
    # ------------------------------------------------------------------

    def _on_download_single(self):
        if not self._preflight():
            return

        self._set_downloading(True)
        song = self.single_song_var.get().strip() or "untitled"
        out = self.output_var.get()
        url = self.info['url']
        meta = {
            'title': song,
            'artist': self.single_artist_var.get().strip(),
            'album': self.single_album_var.get().strip(),
        }

        def _work():
            try:
                self.root.after(0, lambda: self.status_var.set("Downloading..."))

                def _prog(p):
                    self.root.after(0, lambda: self.progress_var.set(p * 100))

                path = downloader.download_track(url, out, song, meta, _prog)
                self.root.after(0, lambda: self._done(True, f"Saved to:\n{path}"))
            except Exception as e:
                self.root.after(0, lambda: self._done(False, f"Download failed:\n{e}"))

        threading.Thread(target=_work, daemon=True).start()

    # ------------------------------------------------------------------
    # Download — playlist
    # ------------------------------------------------------------------

    def _on_download_playlist(self):
        if not self._preflight():
            return

        self._set_downloading(True)
        out = self.output_var.get()

        tracks = []
        for tw in self.track_widgets:
            tracks.append({
                'url': tw['url'],
                'filename': tw['song_var'].get().strip() or f"track_{tw['index']}",
                'metadata': {
                    'title': tw['song_var'].get().strip(),
                    'artist': tw['artist_var'].get().strip(),
                    'album': tw['album_var'].get().strip(),
                    'track_number': tw['index'],
                },
            })

        def _work():
            total = len(tracks)
            ok = 0
            errors = []

            for i, t in enumerate(tracks):
                if self._cancel:
                    break

                self.root.after(0, (
                    lambda i=i, total=total:
                        self.status_var.set(f"Downloading track {i + 1} of {total}...")))

                try:
                    def _prog(p, i=i, total=total):
                        v = (i + p) / total * 100
                        self.root.after(0, lambda v=v: self.progress_var.set(v))

                    downloader.download_track(
                        t['url'], out, t['filename'], t['metadata'], _prog)
                    ok += 1
                except Exception as e:
                    errors.append(f"Track {i + 1}: {e}")

            cancelled = self._cancel

            def _finish():
                if cancelled:
                    self._done(True, f"Cancelled. Downloaded {ok} of {total} tracks.")
                elif errors:
                    self._done(False,
                               f"Downloaded {ok}/{total} tracks.\n\n"
                               f"Errors ({len(errors)}):\n" + "\n".join(errors[:10]))
                else:
                    self._done(True, f"All {ok} tracks downloaded to:\n{out}")

            self.root.after(0, _finish)

        threading.Thread(target=_work, daemon=True).start()

    # ------------------------------------------------------------------
    # Completion
    # ------------------------------------------------------------------

    def _done(self, success, message):
        self._set_downloading(False)
        self.progress_var.set(100 if success else 0)
        self.status_var.set("Done" if success else "Completed with errors")
        if success:
            messagebox.showinfo("Download Complete", message)
        else:
            messagebox.showwarning("Download Issues", message)

    def _check_ffmpeg(self):
        if not downloader.get_ffmpeg_path():
            self.status_var.set("WARNING: ffmpeg not found - downloads will fail")
            messagebox.showwarning(
                "ffmpeg Not Found",
                "ffmpeg is required for audio conversion but was not found.\n\n"
                "Install it:\n"
                "  macOS:   brew install ffmpeg\n"
                "  Windows: winget install ffmpeg\n"
                "  Linux:   sudo apt install ffmpeg\n\n"
                "Then restart YT Strip.")

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def run(self):
        self.root.mainloop()
