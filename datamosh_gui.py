#!/usr/bin/env python3
"""
Entropic — Real Datamosh Native Desktop UI
Runs natively on macOS. No browser. No internet.

Usage:
    python3 datamosh_gui.py

Requires: tkinter (built into Python), ffmpeg (via Homebrew)
"""

import sys
import os
import subprocess
import threading
import time
from pathlib import Path
from tkinter import (
    Tk, Frame, Label, Button, Entry, StringVar, IntVar, DoubleVar,
    filedialog, messagebox, ttk, HORIZONTAL, LEFT, RIGHT, TOP, BOTTOM,
    X, Y, BOTH, W, E, N, S, END, DISABLED, NORMAL, BooleanVar,
)

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.real_datamosh import (
    real_datamosh,
    multi_datamosh,
    preprocess_for_datamosh,
    extract_motion_vectors,
    strategic_keyframes,
    datamosh_with_transforms,
    audio_datamosh,
)
from core.video_io import probe_video


class DatamoshApp:
    """Native desktop datamosh application."""

    def __init__(self, root):
        self.root = root
        self.root.title("Entropic — Real Datamosh")
        self.root.geometry("700x750")
        self.root.minsize(600, 650)

        # State
        self.video_a_path = StringVar()
        self.video_b_path = StringVar()
        self.output_path = StringVar(value=str(Path.home() / "Desktop" / "datamosh_output.mp4"))
        self.mode = StringVar(value="splice")
        self.switch_frame = IntVar(value=30)
        self.width = IntVar(value=640)
        self.height = IntVar(value=480)
        self.fps = DoubleVar(value=30.0)
        self.rotation = DoubleVar(value=0.0)
        self.x_offset = IntVar(value=0)
        self.y_offset = IntVar(value=0)
        self.motion_pattern = StringVar(value="static")
        self.use_audio = BooleanVar(value=False)
        self.audio_mosh_mode = StringVar(value="swap")
        self.audio_intensity = DoubleVar(value=0.3)
        self.processing = False

        self._build_ui()

    def _build_ui(self):
        """Build the native UI."""
        # Main container with padding
        main = Frame(self.root, padx=15, pady=10)
        main.pack(fill=BOTH, expand=True)

        # --- Title ---
        Label(main, text="Entropic — Real Datamosh",
              font=("Menlo", 16, "bold")).pack(anchor=W, pady=(0, 5))
        Label(main, text="H.264 P-frame manipulation. Not simulation.",
              font=("Menlo", 10), fg="gray").pack(anchor=W, pady=(0, 10))

        # --- Video Inputs ---
        input_frame = ttk.LabelFrame(main, text=" Video Inputs ", padding=8)
        input_frame.pack(fill=X, pady=(0, 8))

        self._file_row(input_frame, "Video A (base image):", self.video_a_path, 0)
        self._file_row(input_frame, "Video B (motion source):", self.video_b_path, 1)

        # Info labels
        self.info_a = Label(input_frame, text="", font=("Menlo", 9), fg="gray")
        self.info_a.grid(row=0, column=3, padx=5, sticky=W)
        self.info_b = Label(input_frame, text="", font=("Menlo", 9), fg="gray")
        self.info_b.grid(row=1, column=3, padx=5, sticky=W)

        # --- Mode ---
        mode_frame = ttk.LabelFrame(main, text=" Datamosh Mode ", padding=8)
        mode_frame.pack(fill=X, pady=(0, 8))

        modes = [
            ("splice", "Splice — B's motion warps A's image"),
            ("interleave", "Interleave — Flicker melt between sources"),
            ("replace", "Replace — Random P-frame injection"),
        ]
        for i, (val, desc) in enumerate(modes):
            ttk.Radiobutton(mode_frame, text=desc, value=val,
                            variable=self.mode).grid(row=i, column=0, sticky=W, pady=1)

        # Switch frame / interval
        param_row = Frame(mode_frame)
        param_row.grid(row=len(modes), column=0, sticky=W, pady=(5, 0))
        Label(param_row, text="Switch frame / interval:", font=("Menlo", 10)).pack(side=LEFT)
        ttk.Spinbox(param_row, from_=1, to=9999, textvariable=self.switch_frame,
                     width=6).pack(side=LEFT, padx=5)

        # --- Resolution ---
        res_frame = ttk.LabelFrame(main, text=" Output Settings ", padding=8)
        res_frame.pack(fill=X, pady=(0, 8))

        row1 = Frame(res_frame)
        row1.pack(fill=X)
        Label(row1, text="Width:", font=("Menlo", 10)).pack(side=LEFT)
        ttk.Spinbox(row1, from_=128, to=3840, textvariable=self.width,
                     width=6).pack(side=LEFT, padx=(5, 15))
        Label(row1, text="Height:", font=("Menlo", 10)).pack(side=LEFT)
        ttk.Spinbox(row1, from_=128, to=2160, textvariable=self.height,
                     width=6).pack(side=LEFT, padx=(5, 15))
        Label(row1, text="FPS:", font=("Menlo", 10)).pack(side=LEFT)
        ttk.Spinbox(row1, from_=1, to=120, textvariable=self.fps,
                     width=5, increment=0.1).pack(side=LEFT, padx=5)

        # Preset buttons
        preset_row = Frame(res_frame)
        preset_row.pack(fill=X, pady=(5, 0))
        Label(preset_row, text="Presets:", font=("Menlo", 10)).pack(side=LEFT)
        for label, w, h in [("480p", 854, 480), ("720p", 1280, 720), ("1080p", 1920, 1080)]:
            Button(preset_row, text=label, width=5,
                   command=lambda _w=w, _h=h: self._set_res(_w, _h)).pack(side=LEFT, padx=3)
        Button(preset_row, text="Match A", width=7,
               command=self._match_source_res).pack(side=LEFT, padx=3)

        # Output path
        out_row = Frame(res_frame)
        out_row.pack(fill=X, pady=(5, 0))
        Label(out_row, text="Output:", font=("Menlo", 10)).pack(side=LEFT)
        Entry(out_row, textvariable=self.output_path, font=("Menlo", 10)).pack(
            side=LEFT, fill=X, expand=True, padx=5)
        Button(out_row, text="...", width=3,
               command=self._browse_output).pack(side=LEFT)

        # --- Transforms ---
        xform_frame = ttk.LabelFrame(main, text=" Spatial Transforms ", padding=8)
        xform_frame.pack(fill=X, pady=(0, 8))

        xrow = Frame(xform_frame)
        xrow.pack(fill=X)
        Label(xrow, text="Rotation:", font=("Menlo", 10)).pack(side=LEFT)
        ttk.Spinbox(xrow, from_=-360, to=360, textvariable=self.rotation,
                     width=6, increment=5.0).pack(side=LEFT, padx=(5, 15))
        Label(xrow, text="X offset:", font=("Menlo", 10)).pack(side=LEFT)
        ttk.Spinbox(xrow, from_=-1000, to=1000, textvariable=self.x_offset,
                     width=6).pack(side=LEFT, padx=(5, 15))
        Label(xrow, text="Y offset:", font=("Menlo", 10)).pack(side=LEFT)
        ttk.Spinbox(xrow, from_=-1000, to=1000, textvariable=self.y_offset,
                     width=6).pack(side=LEFT, padx=5)

        mrow = Frame(xform_frame)
        mrow.pack(fill=X, pady=(5, 0))
        Label(mrow, text="Motion pattern:", font=("Menlo", 10)).pack(side=LEFT)
        ttk.Combobox(mrow, textvariable=self.motion_pattern, width=12,
                      values=["static", "sweep_lr", "circular", "random", "pulse"],
                      state="readonly").pack(side=LEFT, padx=5)

        # --- Audio ---
        audio_frame = ttk.LabelFrame(main, text=" Audio ", padding=8)
        audio_frame.pack(fill=X, pady=(0, 8))

        ttk.Checkbutton(audio_frame, text="Keep audio from Video A",
                         variable=self.use_audio).pack(anchor=W)

        arow = Frame(audio_frame)
        arow.pack(fill=X, pady=(3, 0))
        Label(arow, text="Audio mosh:", font=("Menlo", 10)).pack(side=LEFT)
        ttk.Combobox(arow, textvariable=self.audio_mosh_mode, width=10,
                      values=["none", "swap", "blend", "corrupt", "stutter"],
                      state="readonly").pack(side=LEFT, padx=5)
        Label(arow, text="Intensity:", font=("Menlo", 10)).pack(side=LEFT, padx=(10, 0))
        ttk.Scale(arow, from_=0.0, to=1.0, variable=self.audio_intensity,
                   orient=HORIZONTAL, length=120).pack(side=LEFT, padx=5)

        # --- Action ---
        action_frame = Frame(main)
        action_frame.pack(fill=X, pady=(5, 5))

        self.render_btn = Button(
            action_frame, text="DATAMOSH", font=("Menlo", 14, "bold"),
            bg="#FF3333", fg="white", height=2,
            command=self._start_datamosh,
        )
        self.render_btn.pack(fill=X)

        # Progress
        self.progress = ttk.Progressbar(main, mode="indeterminate", length=300)
        self.progress.pack(fill=X, pady=(5, 3))

        self.status_label = Label(main, text="Ready", font=("Menlo", 10), fg="gray")
        self.status_label.pack(anchor=W)

        # Open output button (hidden until done)
        self.open_btn = Button(
            main, text="Open Output", font=("Menlo", 11),
            command=self._open_output, state=DISABLED,
        )
        self.open_btn.pack(fill=X, pady=(5, 0))

    def _file_row(self, parent, label_text, var, row):
        """Create a file selection row."""
        Label(parent, text=label_text, font=("Menlo", 10)).grid(
            row=row, column=0, sticky=W, pady=2)
        Entry(parent, textvariable=var, font=("Menlo", 10), width=35).grid(
            row=row, column=1, sticky=W + E, padx=5, pady=2)
        Button(parent, text="Browse", width=7,
               command=lambda: self._browse_video(var, row)).grid(
            row=row, column=2, pady=2)
        parent.columnconfigure(1, weight=1)

    def _browse_video(self, var, row):
        """Open file dialog for video selection."""
        path = filedialog.askopenfilename(
            title="Select Video",
            filetypes=[
                ("Video files", "*.mp4 *.mov *.avi *.mkv *.webm"),
                ("All files", "*.*"),
            ],
        )
        if path:
            var.set(path)
            self._update_video_info(path, row)

    def _update_video_info(self, path, row):
        """Show video info after selection."""
        try:
            info = probe_video(path)
            text = f"{info['width']}x{info['height']} {info['fps']:.0f}fps {info['duration']:.1f}s"
            label = self.info_a if row == 0 else self.info_b
            label.config(text=text)
        except Exception:
            pass

    def _browse_output(self):
        """Select output file path."""
        path = filedialog.asksaveasfilename(
            title="Save Datamosh Output",
            defaultextension=".mp4",
            filetypes=[("MP4 video", "*.mp4")],
        )
        if path:
            self.output_path.set(path)

    def _set_res(self, w, h):
        self.width.set(w)
        self.height.set(h)

    def _match_source_res(self):
        """Match output resolution to Video A."""
        path = self.video_a_path.get()
        if not path or not Path(path).exists():
            return
        try:
            info = probe_video(path)
            self.width.set(info["width"])
            self.height.set(info["height"])
            self.fps.set(info["fps"])
        except Exception:
            pass

    def _start_datamosh(self):
        """Start datamosh processing in a background thread."""
        if self.processing:
            return

        # Validate inputs
        va = self.video_a_path.get()
        vb = self.video_b_path.get()
        out = self.output_path.get()

        if not va or not Path(va).exists():
            messagebox.showerror("Error", "Video A not found. Select a valid video file.")
            return
        if not vb or not Path(vb).exists():
            messagebox.showerror("Error", "Video B not found. Select a valid video file.")
            return
        if not out:
            messagebox.showerror("Error", "Set an output path.")
            return

        self.processing = True
        self.render_btn.config(state=DISABLED, text="PROCESSING...")
        self.open_btn.config(state=DISABLED)
        self.progress.start(10)
        self.status_label.config(text="Datamoshing...", fg="orange")

        thread = threading.Thread(target=self._run_datamosh, daemon=True)
        thread.start()

    def _run_datamosh(self):
        """Execute datamosh in background thread."""
        try:
            va = self.video_a_path.get()
            vb = self.video_b_path.get()
            out = self.output_path.get()
            mode = self.mode.get()
            rot = self.rotation.get()
            xoff = self.x_offset.get()
            yoff = self.y_offset.get()
            mp = self.motion_pattern.get()
            audio = va if self.use_audio.get() else None

            t0 = time.time()

            # Choose engine based on transforms
            has_transforms = rot != 0 or xoff != 0 or yoff != 0 or mp != "static"

            if has_transforms:
                result = datamosh_with_transforms(
                    va, vb, out,
                    mode=mode,
                    switch_frame=self.switch_frame.get(),
                    width=self.width.get(),
                    height=self.height.get(),
                    fps=self.fps.get(),
                    rotation=rot,
                    x_offset=xoff,
                    y_offset=yoff,
                    motion_pattern=mp,
                    audio_source=audio,
                )
            else:
                result = real_datamosh(
                    va, vb, out,
                    switch_frame=self.switch_frame.get(),
                    width=self.width.get(),
                    height=self.height.get(),
                    fps=self.fps.get(),
                    mode=mode,
                    audio_source=audio,
                )

            # Audio datamosh if requested
            amosh = self.audio_mosh_mode.get()
            if amosh != "none" and audio:
                self.root.after(0, lambda: self.status_label.config(
                    text="Audio moshing...", fg="orange"))
                audio_datamosh(
                    str(result), va, vb, out,
                    intensity=self.audio_intensity.get(),
                    mode=amosh,
                )

            elapsed = time.time() - t0
            size_kb = Path(out).stat().st_size / 1024

            self.root.after(0, lambda: self._done(
                f"Done! {size_kb:.0f} KB in {elapsed:.1f}s"))

        except Exception as e:
            self.root.after(0, lambda: self._error(str(e)))

    def _done(self, msg):
        """Called on main thread when processing completes."""
        self.processing = False
        self.progress.stop()
        self.render_btn.config(state=NORMAL, text="DATAMOSH")
        self.open_btn.config(state=NORMAL)
        self.status_label.config(text=msg, fg="green")

    def _error(self, msg):
        """Called on main thread when processing fails."""
        self.processing = False
        self.progress.stop()
        self.render_btn.config(state=NORMAL, text="DATAMOSH")
        self.status_label.config(text=f"Error: {msg[:80]}", fg="red")
        messagebox.showerror("Datamosh Error", msg)

    def _open_output(self):
        """Open the output file with macOS default viewer."""
        out = self.output_path.get()
        if out and Path(out).exists():
            subprocess.run(["open", out])


def main():
    root = Tk()
    # macOS-specific styling
    try:
        root.tk.call("::tk::unsupported::MacWindowStyle", "style", root._w, "document", "closeBox collapseBox")
    except Exception:
        pass
    app = DatamoshApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
