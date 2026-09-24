import json
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import ttk, messagebox

from search_runner import clear_download_history, get_downloads_root, get_manifest_path, run_search


def get_workspace_root():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


WORKSPACE_ROOT = get_workspace_root()
DATA_DIR = WORKSPACE_ROOT / "data"
ARTISTS_FILE = DATA_DIR / "artists.json"


def should_show_artist_placeholder(entry_value, has_focus):
    return not entry_value and not has_focus


class App:
    def __init__(self, root):
        self.root = root
        root.title("DJ Extractor")
        root.geometry("540x520")
        root.minsize(540, 520)

        bg = "#101116"
        fg = "#f4f7fb"
        entry_bg = "#171b27"
        card_bg = "#171b27"
        accent = "#6d7cff"
        accent_soft = "#3f4ff0"
        muted = "#8fa1bd"

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TButton", font=(None, 10, "bold"), padding=(8, 6), background=accent_soft, foreground=fg)
        style.map("TButton", background=[('active', '#4e5ff5'), ('pressed', '#3444d9')], foreground=[('disabled', '#777777')])
        style.configure("Accent.TButton", font=(None, 10, "bold"), padding=(8, 6), background=accent, foreground="white")
        style.map("Accent.TButton", background=[('active', '#808dff'), ('pressed', '#5160e5')])
        style.configure("Large.TLabel", font=(None, 22, "bold"), foreground=fg, background=bg)
        style.configure("Subtitle.TLabel", font=(None, 10), foreground=muted, background=bg)
        style.configure("Card.TFrame", background=card_bg)
        style.configure("TFrame", background=bg)
        style.configure("TLabel", foreground=fg, background=bg)
        style.configure("TEntry", fieldbackground=entry_bg, foreground=fg)
        style.configure("TCheckbutton", font=(None, 12), background=bg, foreground=fg)
        style.configure("Toggle.TButton", font=(None, 11, "bold"), padding=(10, 6), background="#2b3148", foreground=fg)
        style.map("Toggle.TButton", background=[('active', '#3e4d7d'), ('pressed', '#303d6c')], foreground=[('disabled', '#777777')])
        style.configure("Treeview", background="#1b1f2d", fieldbackground="#1b1f2d", foreground=fg, rowheight=28)
        style.configure("Treeview.Heading", background="#23293b", foreground="#f4f7fb")
        style.configure("Artist.Vertical.TScrollbar", background="#5a6de0", troughcolor="#171b27", arrowcolor="#f4f7fb", bordercolor="#2a3042")
        style.map("Artist.Vertical.TScrollbar", background=[('active', '#7586ff'), ('pressed', '#4b5fe7')])
        style.map("Treeview", background=[('selected', accent)])

        root.configure(bg=bg)
        main = ttk.Frame(root, padding=18, style="TFrame")
        main.pack(fill="both", expand=True)

        header = ttk.Frame(main, style="TFrame")
        header.pack(fill="x", pady=(0, 12))
        title = ttk.Label(header, text="DJ Extractor", style="Large.TLabel")
        title.pack(anchor="w")
        subtitle = ttk.Label(header, text="Add artists and select desired difficulty (uncheck all to ignore difficulty filter).", style="Subtitle.TLabel")
        subtitle.pack(anchor="w", pady=(4, 0))

        lib_card = ttk.Frame(main, padding=10, style="Card.TFrame")
        lib_card.pack(fill="x", pady=(0, 10))

        lib_header = ttk.Frame(lib_card, style="Card.TFrame")
        lib_header.pack(fill="x", pady=(0, 8))
        lib_title = ttk.Label(lib_header, text="Artist Library", font=(None, 15, "bold"), anchor="w", foreground=fg, background=card_bg)
        lib_title.pack(side="left")

        lib_body = ttk.Frame(lib_card, style="Card.TFrame")
        lib_body.pack(fill="x")

        self.listbox_height = 6
        self.listbox_width = 40
        self.listbox = tk.Listbox(
            lib_body,
            font=(None, 12),
            activestyle="none",
            selectmode="extended",
            height=self.listbox_height,
            width=self.listbox_width,
            bg="#202433",
            fg=fg,
            bd=0,
            highlightthickness=0,
            selectbackground=accent,
            selectforeground="white",
        )
        self.listbox.pack(side="left", fill="both", expand=True)
        self.listbox.bind("<Double-Button-1>", self.edit_selected_artist)
        self.clear_list_label = tk.Label(
            self.listbox,
            text="- Clear List -",
            fg=muted,
            bg="#202433",
            cursor="hand2",
            font=(None, 9, "bold"),
            justify="right",
            anchor="ne",
        )
        self.clear_list_label.place(relx=1.0, rely=0.0, anchor="ne", x=-6, y=4)
        self.clear_list_label.bind("<Button-1>", lambda event: self.clear_library())

        self.lb_scroll = ttk.Scrollbar(lib_body, style="Artist.Vertical.TScrollbar", command=self.listbox.yview)
        self.lb_scroll.pack(side="left", fill="y", padx=(6, 0))
        self.listbox.config(yscrollcommand=self.lb_scroll.set)
        self.update_listbox_scrollbar()

        controls = ttk.Frame(lib_body, style="Card.TFrame")
        controls.pack(side="right", fill="y", padx=(10, 0))

        diff_panel = ttk.Frame(controls, style="Card.TFrame")
        diff_panel.pack(side="top", fill="x")
        diff_label = ttk.Label(diff_panel, text="Difficulty", font=(None, 13, "bold"), foreground=fg, background=card_bg)
        diff_label.pack(anchor="center", pady=(0, 6))

        self.d_vars = {}
        for d in ["Easy", "Medium", "Hard", "Expert"]:
            var = tk.IntVar(value=1)
            cb = ttk.Checkbutton(diff_panel, text=d, variable=var, style="TCheckbutton")
            cb.pack(anchor="center", pady=2)
            self.d_vars[d.lower()] = var

        toggle_frame = ttk.Frame(diff_panel, style="Card.TFrame")
        toggle_frame.pack(fill="x", pady=(6, 0))
        self.toggle_difficulties_btn = tk.Button(
            toggle_frame,
            text="Uncheck All",
            command=self.toggle_difficulties,
            bg="#1b2031",
            fg=fg,
            activebackground="#2d3756",
            activeforeground=fg,
            relief="solid",
            bd=1,
            highlightthickness=1,
            highlightbackground="#4f5d85",
            highlightcolor="#7d8cff",
            padx=10,
            pady=6,
            font=(None, 10, "bold"),
            width=11,
            cursor="hand2",
        )
        self.toggle_difficulties_btn.pack(anchor="center")

        self.artist_var = tk.StringVar()
        self._artist_placeholder_visible = False
        add_row = ttk.Frame(lib_card, style="Card.TFrame")
        add_row.pack(fill="x", pady=(8, 0))
        self.artist_entry = ttk.Entry(add_row, textvariable=self.artist_var, font=(None, 10), width=18)
        self.artist_entry.pack(side="left", fill="x", expand=True, ipady=3)
        self.artist_entry.bind('<Return>', lambda e: self.add_artist())
        self.artist_entry.bind('<FocusIn>', self._clear_placeholder)
        self.artist_entry.bind('<FocusOut>', self._restore_placeholder)
        self.artist_entry.bind('<KeyRelease>', self._on_entry_key_release)
        self._placeholder_text = "Enter artist name"
        self.artist_entry.configure(foreground="#f4f7fb")
        self.root.after(50, lambda: self._restore_placeholder_if_idle())
        self.artist_entry.focus()
        self.add_artist_btn = ttk.Button(add_row, text="Add Artist", command=self.add_artist, style="Accent.TButton")
        self.add_artist_btn.configure(width=12)
        self.add_artist_btn.pack(side="left", padx=(8, 0))

        action_card = ttk.Frame(main, padding=14, style="Card.TFrame")
        action_card.pack(fill="x")

        action_row = ttk.Frame(action_card, style="Card.TFrame")
        action_row.pack(fill="x")
        self.view_history_btn = ttk.Button(action_row, text="View History", command=self.show_downloaded_files, style="TButton")
        self.view_history_btn.configure(width=8)
        self.view_history_btn.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.search_btn = ttk.Button(action_row, text="Download Charts", command=self.start_search, style="Accent.TButton")
        self.search_btn.configure(width=18)
        self.search_btn.pack(side="left", fill="x", expand=True, padx=8)
        self.open_downloads_btn = ttk.Button(action_row, text="Open Folder", command=self.open_downloads_folder, style="TButton")
        self.open_downloads_btn.configure(width=8)
        self.open_downloads_btn.pack(side="left", fill="x", expand=True, padx=(8, 0))
        self.status_var = tk.StringVar(value="Ready For Download")
        self.status_label = ttk.Label(action_card, textvariable=self.status_var, style="Subtitle.TLabel", font=(None, 10, "bold"))
        self.status_label.pack(anchor="center", pady=(8, 0))

        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.load_artists()

    def _set_artist_placeholder(self, entry_widget):
        if not entry_widget:
            return
        has_focus = entry_widget == entry_widget.focus_get()
        if should_show_artist_placeholder(entry_widget.get(), has_focus):
            if not self._artist_placeholder_visible:
                entry_widget.delete(0, tk.END)
                entry_widget.insert(0, self._placeholder_text)
                self._artist_placeholder_visible = True
            entry_widget.configure(foreground="#8fa1bd")
            return

        if self._artist_placeholder_visible:
            entry_widget.delete(0, tk.END)
            self._artist_placeholder_visible = False
        entry_widget.configure(foreground="#f4f7fb")

    def _restore_placeholder_if_idle(self):
        self._set_artist_placeholder(self.artist_entry)

    def _on_entry_key_release(self, event):
        self._set_artist_placeholder(event.widget)

    def _clear_placeholder(self, event):
        widget = event.widget
        if self._artist_placeholder_visible:
            widget.delete(0, tk.END)
            self._artist_placeholder_visible = False
        widget.configure(foreground="#f4f7fb")

    def _restore_placeholder(self, event):
        widget = event.widget
        self._set_artist_placeholder(widget)

    def update_listbox_scrollbar(self):
        if self.listbox.size() > self.listbox_height:
            self.lb_scroll.pack(side="left", fill="y", padx=(6, 0))
            self.listbox.config(yscrollcommand=self.lb_scroll.set)
        else:
            self.lb_scroll.pack_forget()
            self.listbox.config(yscrollcommand=None)

    def load_artists(self):
        if ARTISTS_FILE.exists():
            try:
                with open(ARTISTS_FILE, "r", encoding="utf-8") as f:
                    artists = json.load(f)
            except Exception:
                artists = []
        else:
            artists = []
        self.listbox.delete(0, tk.END)
        for a in artists:
            self.listbox.insert(tk.END, a)
        self.update_listbox_scrollbar()

    def save_artists(self):
        artists = list(self.listbox.get(0, tk.END))
        with open(ARTISTS_FILE, "w", encoding="utf-8") as f:
            json.dump(artists, f, ensure_ascii=False, indent=2)
        self.update_listbox_scrollbar()

    def add_artist(self):
        name = self.artist_var.get().strip()
        if not name or name == self._placeholder_text:
            return
        existing = list(self.listbox.get(0, tk.END))
        if name in existing:
            messagebox.showinfo("Info", f"'{name}' is already in the library.")
            return
        self.listbox.insert(tk.END, name)
        self.artist_var.set("")
        self._artist_placeholder_visible = False
        self.save_artists()
        self.artist_entry.configure(foreground="#f4f7fb")
        self.artist_entry.delete(0, tk.END)
        self.artist_entry.focus_set()
        self.root.after(0, lambda: self._set_artist_placeholder(self.artist_entry))

    def edit_selected_artist(self, event=None):
        selection = list(self.listbox.curselection())
        if not selection:
            return
        index = selection[0]
        current_name = self.listbox.get(index)
        self.open_artist_edit_dialog(index, current_name)

    def open_artist_edit_dialog(self, index, current_name):
        popup = tk.Toplevel(self.root)
        popup.title("Edit Artist")
        popup.geometry("340x190")
        popup.minsize(320, 170)
        popup.configure(bg="#12141c")
        popup.transient(self.root)
        popup.grab_set()

        content = ttk.Frame(popup, padding=16, style="Card.TFrame")
        content.pack(fill="both", expand=True)

        ttk.Label(content, text="Artist Name", font=(None, 11, "bold"), foreground="#f4f7fb", background="#171b27").pack(anchor="w")

        name_var = tk.StringVar(value=current_name)
        name_entry = ttk.Entry(content, textvariable=name_var, font=(None, 11), width=30)
        name_entry.pack(fill="x", pady=(6, 12), ipady=3)
        name_entry.focus_set()
        name_entry.selection_range(0, tk.END)

        def save_artist_name():
            new_name = (name_var.get() or "").strip()
            if not new_name:
                messagebox.showwarning("Artist name", "Artist name cannot be empty.")
                return

            existing = [item for i, item in enumerate(self.listbox.get(0, tk.END)) if i != index]
            if new_name in existing:
                messagebox.showinfo("Info", f"'{new_name}' is already in the library.")
                return

            self.listbox.delete(index)
            self.listbox.insert(index, new_name)
            self.save_artists()
            popup.destroy()

        def delete_artist_name():
            if messagebox.askyesno("Delete Artist", f"Remove '{current_name}' from the library?"):
                self.listbox.delete(index)
                self.save_artists()
                popup.destroy()

        buttons = ttk.Frame(content, style="Card.TFrame")
        buttons.pack(fill="x")
        save_btn = ttk.Button(buttons, text="Save", command=save_artist_name, style="Accent.TButton")
        save_btn.pack(side="left")
        delete_btn = ttk.Button(buttons, text="Delete", command=delete_artist_name, style="TButton")
        delete_btn.pack(side="left", padx=(8, 0))
        cancel_btn = ttk.Button(buttons, text="Cancel", command=popup.destroy, style="TButton")
        cancel_btn.pack(side="right")

        name_entry.bind("<Return>", lambda event: save_artist_name())

    def remove_selected(self):
        sel = list(self.listbox.curselection())
        for i in reversed(sel):
            self.listbox.delete(i)
        self.save_artists()

    def clear_library(self):
        if messagebox.askyesno("Confirm", "Clear the entire artist library?"):
            self.listbox.delete(0, tk.END)
            self.save_artists()

    def toggle_difficulties(self):
        current_state = self.toggle_difficulties_btn.cget("text")
        if current_state == "Uncheck All":
            new_state = 0
            self.toggle_difficulties_btn.configure(text="Check All")
        else:
            new_state = 1
            self.toggle_difficulties_btn.configure(text="Uncheck All")
        for var in self.d_vars.values():
            var.set(new_state)

    def open_downloads_folder(self):
        try:
            folder = get_downloads_root()
            folder.mkdir(parents=True, exist_ok=True)
            if sys.platform.startswith("win"):
                import os
                os.startfile(str(folder))
            elif sys.platform == "darwin":
                import subprocess
                subprocess.Popen(["open", str(folder)])
            else:
                import subprocess
                subprocess.Popen(["xdg-open", str(folder)])
        except Exception as e:
            messagebox.showerror("Downloads", f"Could not open downloads folder: {e}")

    def start_search(self):
        artists = list(self.listbox.get(0, tk.END))
        if not artists:
            messagebox.showwarning("No artists", "Add at least one artist to search for.")
            return
        difficulties = {k: bool(v.get()) for k, v in self.d_vars.items()}

        self.set_ui_state("disabled")
        self.update_status("Starting search...")

        def worker():
            try:
                summary = run_search(artists, difficulties, on_progress=self.handle_progress)
                self.root.after(0, self.on_search_complete, summary)
            except Exception as e:
                self.root.after(0, self.on_search_complete, {"error": str(e)})

        t = threading.Thread(target=worker, daemon=True)
        t.start()

    def show_downloaded_files(self):
        manifest_path = get_manifest_path()
        if not manifest_path.exists():
            messagebox.showinfo("Downloaded Files", "No files have been recorded yet.")
            return
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                entries = json.load(f)
        except Exception as e:
            messagebox.showerror("Downloaded Files", f"Could not read manifest: {e}")
            return

        popup = tk.Toplevel(self.root)
        popup.title("Downloads")
        popup.geometry("430x540")
        popup.minsize(430, 540)
        popup.configure(bg="#12141c")

        style = ttk.Style(popup)
        style.theme_use("clam")
        style.configure("Downloaded.TFrame", background="#14161e")
        style.configure("Downloaded.TLabel", foreground="#f4f7fb", background="#14161e")
        style.configure("Downloaded.TButton", font=(None, 11, "bold"), padding=(12, 8), background="#2b2f43", foreground="#f4f7fb")
        style.map("Downloaded.TButton", background=[("active", "#3a4262")], foreground=[("disabled", "#777777")])
        style.configure("Downloaded.Treeview", background="#1b1f2d", fieldbackground="#1b1f2d", foreground="#f4f7fb")
        style.configure("Downloaded.Treeview.Heading", background="#23293b", foreground="#f4f7fb")

        container = ttk.Frame(popup, padding=18, style="Downloaded.TFrame")
        container.pack(fill="both", expand=True)

        header = ttk.Frame(container, style="Downloaded.TFrame")
        header.pack(fill="x", pady=(0, 8))
        ttk.Label(header, text="Downloads", font=(None, 20, "bold"), style="Downloaded.TLabel").pack(anchor="w")
        ttk.Label(header, text="Your tracked downloads are grouped by artist.", style="Downloaded.TLabel").pack(anchor="w", pady=(2, 0))

        grouped = {}
        for entry in entries:
            artist = (entry.get("artist") or "Unknown Artist").strip() or "Unknown Artist"
            grouped.setdefault(artist, []).append(entry)

        count_label = ttk.Label(container, text=f"{len(entries)} tracked downloads across {len(grouped)} artist(s)", style="Downloaded.TLabel")
        count_label.pack(anchor="w", pady=(0, 8))

        tree_card = ttk.Frame(container, padding=10, style="Downloaded.TFrame")
        tree_card.pack(fill="both", expand=True)

        tree = ttk.Treeview(tree_card, show="tree", style="Downloaded.Treeview")
        tree.pack(side="left", fill="both", expand=True)
        tree.heading("#0", text="Artist")
        tree.column("#0", width=360, anchor="w")
        tree.configure(selectmode="extended")

        y_scroll = ttk.Scrollbar(tree_card, orient="vertical", command=tree.yview)
        y_scroll.pack(side="right", fill="y")
        tree.configure(yscrollcommand=y_scroll.set)

        for artist, artist_entries in sorted(grouped.items(), key=lambda item: item[0].lower()):
            artist_id = tree.insert("", "end", text=f"{artist} ({len(artist_entries)})", open=False)
            for entry in sorted(artist_entries, key=lambda item: (item.get("title") or "").lower()):
                raw_title = entry.get("title") or entry.get("filename") or "Untitled"
                song_title = raw_title
                if isinstance(raw_title, str):
                    prefix = f"{artist} - "
                    if raw_title.lower().startswith(prefix.lower()):
                        song_title = raw_title[len(prefix):]
                tree.insert(artist_id, "end", text=f"  {song_title}")

        button_frame = ttk.Frame(container, style="Downloaded.TFrame")
        button_frame.pack(fill="x", pady=(10, 0))

        remove_btn = ttk.Button(button_frame, text="Remove Selected", command=lambda: self.remove_selected_downloads(manifest_path, popup, tree), style="Downloaded.TButton")
        remove_btn.pack(side="left")
        clear_btn = ttk.Button(button_frame, text="Clear All", command=lambda: self.clear_downloaded_files(manifest_path, popup), style="Downloaded.TButton")
        clear_btn.pack(side="left", padx=(8, 0))
        close_btn = ttk.Button(button_frame, text="Close", command=popup.destroy, style="Downloaded.TButton")
        close_btn.pack(side="right")

        popup.transient(self.root)
        popup.grab_set()

    def remove_selected_downloads(self, manifest_path, popup, tree):
        selected_items = tree.selection()
        if not selected_items:
            messagebox.showinfo("Downloads", "Select one or more entries to remove.")
            return

        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                entries = json.load(f)
        except Exception:
            entries = []

        remaining = []
        for entry in entries:
            artist = (entry.get("artist") or "Unknown Artist").strip() or "Unknown Artist"
            title = entry.get("title") or entry.get("filename") or "Untitled"
            remove_entry = False
            for item_id in selected_items:
                parent_id = tree.parent(item_id)
                if parent_id == "":
                    if artist == tree.item(item_id, "text").split(" (", 1)[0]:
                        remove_entry = True
                        break

                item_text = (tree.item(item_id, "text") or "").strip()
                item_artist = tree.item(parent_id, "text").split(" (", 1)[0] if parent_id else artist
                item_title = item_text
                if artist == item_artist and title == item_title:
                    remove_entry = True
                    break

            if not remove_entry:
                remaining.append(entry)

        try:
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(remaining, f, ensure_ascii=False, indent=2)
        except Exception as e:
            messagebox.showerror("Downloads", f"Could not update history: {e}")
            return

        if popup is not None:
            popup.destroy()
        self.show_downloaded_files()

    def clear_downloaded_files(self, manifest_path, popup=None):
        if not messagebox.askyesno("Confirm", "Clear the tracked downloaded-files list?"):
            return
        try:
            manifest = []
            clear_download_history(manifest, manifest_path)
        except Exception as e:
            messagebox.showerror("Downloaded Files", f"Could not clear manifest: {e}")
            return
        if popup is not None:
            popup.destroy()
        self.show_downloaded_files()

    def set_ui_state(self, state):
        for w in [self.search_btn, self.view_history_btn, self.open_downloads_btn, self.toggle_difficulties_btn]:
            try:
                w.config(state=state)
            except Exception:
                pass

    def handle_progress(self, text):
        message = str(text or "").strip()
        if not message:
            return

        lower = message.lower()
        keep = (
            "starting search" in lower
            or "searching for:" in lower
            or "downloaded " in lower
            or "skipping '" in lower
            or "skipping \"" in lower
            or lower.endswith("done.")
        )
        if not keep:
            return

        self.root.after(0, self.update_status, message)

    def update_status(self, text):
        message = str(text or "Ready").strip() or "Ready"
        if message.lower().endswith("done."):
            message = message[:-5].strip() or "Done"
        self.status_var.set(message)
        self.root.title(f"DJ Extractor — {message}")

    def on_search_complete(self, result):
        # result may be a dict summary or an error string
        if isinstance(result, dict):
            if "error" in result:
                msg = f"Error: {result['error']}"
            else:
                artists_processed = result.get("artists_processed", 0)
                artists_found = result.get("artists_found", [])
                files_downloaded = result.get("files_downloaded", 0)
                msg = (
                    f"Processed {artists_processed} artist(s). "
                    f"Found: {len(artists_found)}. "
                    f"Files downloaded: {files_downloaded}."
                )
        else:
            msg = str(result)

        self.update_status(msg)
        self.set_ui_state("normal")


def main():
    root = tk.Tk()
    app = App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
