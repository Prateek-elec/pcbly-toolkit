import math
import ttkbootstrap as tb
from ttkbootstrap.constants import *
from tkinter import filedialog, messagebox
import matplotlib
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt

# --- Tooltip helper ---
import tkinter as tk

class ToolTip(object):
    """Create a tooltip for a given widget"""
    def __init__(self, widget, text='widget info'):
        self.widget = widget
        self.text = text
        self.tipwindow = None
        self.widget.bind("<Enter>", self.show_tip)
        self.widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, event=None):
        if self.tipwindow or not self.text: return
        x, y, _, cy = self.widget.bbox("insert") if hasattr(self.widget, 'bbox') else (0,0,0,0)
        x = x + self.widget.winfo_rootx() + 20
        y = y + self.widget.winfo_rooty() + cy + 28
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, background="#22272e", foreground="#e0f6ff",
                         relief=tk.SOLID, borderwidth=1, font=("Segoe UI", 9))
        label.pack(ipadx=7, ipady=3)

    def hide_tip(self, event=None):
        tw = self.tipwindow
        self.tipwindow = None
        if tw: tw.destroy()

# --- Engineering Model ---
class PCBModel:
    @staticmethod
    def ipc2152_trace_width(current, copper_um, temp_rise, is_ext):
        K = 0.024 if is_ext else 0.012
        area_mm2 = K * (current ** 0.44) * (temp_rise ** -0.725)
        return area_mm2 / (copper_um / 1000)

    @staticmethod
    def via_recommend(current, pcb_thick, plating_um, temp_rise, n_vias=1):
        diameters = [0.2, 0.25, 0.3, 0.4, 0.5, 0.6, 0.8]
        rec = []
        for d in diameters:
            t_mm = plating_um / 1000.0
            out_d = d + 2 * t_mm
            area_mm2 = math.pi * ((out_d/2)**2 - (d/2)**2)
            resistance = 1.68e-8 * (pcb_thick / 1000) / (area_mm2 * 1e-6)
            ampacity = math.sqrt(temp_rise / (resistance * 0.024))
            total_cap = ampacity * n_vias
            ar = pcb_thick / d
            pad = d + 0.4
            ok = (total_cap >= current and ar <= 10)
            rec.append((f"{d:.2f}", f"{pad:.2f}", f"{ampacity:.2f}", f"{ar:.1f}", "✔" if ok else ""))
        return rec

    @staticmethod
    def impedance_microstrip(w, h, t, er):
        weff = w + t / math.pi * math.log(1 + 4 * math.e / (t / h + (1 / math.pi)))
        eps_eff = (er + 1)/2 + (er - 1)/2 * (1 / math.sqrt(1 + 12 * h / w))
        return (60 / math.sqrt(eps_eff)) * math.log(8 * h / (weff + t))

    @staticmethod
    def voltage_drop(width, copper_um, length, current):
        thick = copper_um / 1000
        resistivity = 1.68e-8
        area_mm2 = width * thick
        resistance = resistivity * (length / 1000) / (area_mm2 * 1e-6)
        vdrop = current * resistance
        return resistance, vdrop, current * vdrop

    @staticmethod
    def clearance_ipc2221(voltage, loc="external_uncoated"):
        tables = {
            "internal":   [(15,0.05), (30,0.05), (50,0.1), (100,0.1), (150,0.2), (250,0.2), (500,0.25), (9999,lambda v:0.0005*v)],
            "external_uncoated": [(15,0.1), (30,0.1), (50,0.6), (100,0.6), (150,0.6), (250,1.25), (500,2.5), (9999,lambda v:0.005*v)],
            "external_coated": [(15,0.05), (30,0.05), (50,0.13), (100,0.13), (150,0.4), (250,0.4), (500,0.8), (9999,lambda v:0.00305*v)]
        }
        for max_v, val in tables[loc]:
            if voltage <= max_v:
                return val(voltage) if callable(val) else val
        return 10.0

def validate_float(inp):
    try: float(inp); return True
    except: return False

# --- GUI Class ---
class PCBToolkitGUI(tb.Window):
    def __init__(self):
        super().__init__(themename="superhero")
        self.title("PCBly")
        self.geometry("1150x700")
        self.materials = {'FR-4': 4.4, 'Rogers 4350B': 3.48, 'Polyimide': 3.5}
        self.calc_results = {}
        self.frames = {}
        self.theme_mode = "superhero"

        topbar = tb.Frame(self, bootstyle="dark")
        topbar.pack(side="top", fill="x")
        tb.Label(topbar, text="Your friendly PCB sidekick", font=("Segoe UI", 17, "bold"),
                 bootstyle="inverse-info").pack(side="left", padx=10, pady=10)
        tb.Label(topbar, text="Theme:", font=("Segoe UI",11)).pack(side="right", padx=2)
        themecombo = tb.Combobox(topbar, values=["superhero","cyborg","flatly","cosmo","darkly","morph"], state="readonly")
        themecombo.set(self.theme_mode)
        themecombo.pack(side="right", padx=3)
        themecombo.bind("<<ComboboxSelected>>", lambda e: self.switch_theme(themecombo.get()))

        # Sidebar navigation with tooltips
        sidebar = tb.Frame(self, bootstyle="dark")
        sidebar.pack(side="left", fill="y", padx=0)
        self.sections = ["Trace Width", "Via Recommendation", "Impedance", "Voltage Drop", "Clearance", "Best Scenario"]
        side_hints = [
            "Calculate safe PCB trace width for your current/temperature.",
            "Find best via size/count for ampacity and thermal compliance.",
            "Impedance calculator for microstrip (RF/high-speed lines).",
            "Compute trace voltage drop and total power loss.",
            "Creepage/clearance checker per IPC-2221B.",
            "Suggests best design options based on results."
        ]
        self.nav_buttons = []
        for ix, label in enumerate(self.sections):
            b = tb.Button(sidebar, text=label, width=20, bootstyle="primary-outline",
                          command=lambda i=ix: self.show_section(i))
            b.pack(pady=2, padx=0, anchor="n")
            ToolTip(b, side_hints[ix])
            self.nav_buttons.append(b)
        self.content = tb.Frame(self, bootstyle="light")
        self.content.pack(side="left", fill="both", expand=True,padx=0,pady=0)

        self.create_trace_page()
        self.create_via_page()
        self.create_imp_page()
        self.create_vdrop_page()
        self.create_clearance_page()
        self.create_scenario_page()
        self.show_section(0)
        btn = tb.Button(self, text="Export Results", bootstyle="success-outline", command=self.export_results)
        btn.pack(side="bottom", pady=8)
        ToolTip(btn, "Export all calculation results as a report file.")

    def switch_theme(self, name):
        self.theme_mode = name
        self.style.theme_use(name)

    def show_section(self, idx):
        for f in self.frames.values():
            f.pack_forget()
        lbl = self.sections[idx]
        f = self.frames[lbl]
        f.pack(fill="both", expand=True)
        for b in self.nav_buttons:
            b.config(bootstyle="primary-outline")
        self.nav_buttons[idx].config(bootstyle="primary")

    # -- TRACE --
    def create_trace_page(self):
        f = tb.Frame(self.content)
        self.frames["Trace Width"] = f
        group = tb.Labelframe(f, text="Input", bootstyle="info", padding=(12,8))
        group.pack(side="left", fill="y", pady=30, padx=30)
        vcmd = (self.register(validate_float), '%P')
        self.trace_vars = [tb.StringVar(value="1"), tb.StringVar(value="35"), tb.StringVar(value="20")]
        labels = ["Current", "Copper", "Temp Rise"]
        units = ["A", "μm", "°C"]
        hints = ["Trace current (in Amps)", "Copper thickness in microns (35μm = 1oz)", "Temperature rise allowed above ambient."]
        for i, (lbl, unit) in enumerate(zip(labels, units)):
            tb.Label(group, text=f"{lbl}:", font=("Segoe UI",11)).grid(row=i,column=0,sticky="e",pady=4)
            e = tb.Entry(group, textvariable=self.trace_vars[i], width=10, validate='key', validatecommand=vcmd)
            e.grid(row=i,column=1,sticky="ew",padx=2)
            tb.Label(group, text=unit, width=5, anchor="w",font=("Segoe UI", 11), foreground="#7C7C8B"
                     ).grid(row=i,column=2,sticky="w")
            ToolTip(e, hints[i])
        self.trace_ext = tb.BooleanVar(value=True)
        cb = tb.Checkbutton(group,text="External",variable=self.trace_ext, bootstyle="info-round-toggle")
        cb.grid(row=3,column=0,columnspan=3,pady=7,sticky="w")
        ToolTip(cb, "Check if trace is on PCB outer layer.")
        calcbtn = tb.Button(group,text="Calculate",bootstyle="success", command=self.calc_trace)
        ToolTip(calcbtn,"Calculate safe minimum width for the entered current and copper.")
        calcbtn.grid(row=6, column=0, columnspan=3, pady=14)
        resplot = tb.Labelframe(f, text="Result & Graph", bootstyle="info", padding=(10,8))
        resplot.pack(side="left", fill="both", expand=True, pady=30, padx=(0,30))
        self.trace_res = tb.Text(resplot, height=4, width=48, font=("Consolas", 12), state="disabled")
        self.trace_res.pack(anchor="nw", pady=2)
        self.trace_fig = plt.Figure(figsize=(3.6,3.2), dpi=90)
        self.trace_ax = self.trace_fig.add_subplot(111)
        self.trace_canvas = FigureCanvasTkAgg(self.trace_fig, master=resplot)
        self.trace_canvas.get_tk_widget().pack(anchor="nw", pady=8)

    def calc_trace(self):
        cur, cu, dT = map(float, [v.get() for v in self.trace_vars])
        w = PCBModel.ipc2152_trace_width(cur, cu, dT, self.trace_ext.get())
        self.trace_res.config(state="normal"); self.trace_res.delete("1.0","end")
        self.trace_res.insert("end",f"Required width: {w:.3f} mm (IPC-2152)\n")
        self.trace_res.config(state="disabled")
        self.trace_ax.clear()
        I = [i * 0.2 for i in range(1, 26)]
        W = [PCBModel.ipc2152_trace_width(i, cu, dT, self.trace_ext.get()) for i in I]
        self.trace_ax.plot(I, W, 'o-', color="#18c3d8", linewidth=2)
        self.trace_ax.set_xlabel("Current (A)")
        self.trace_ax.set_ylabel("Width (mm)")
        self.trace_ax.set_title("Trace Width vs Current (IPC-2152)", fontsize=11)
        self.trace_ax.grid(True)
        self.trace_canvas.draw()
        self.calc_results['trace'] = self.trace_res
        self.update_recommendation()

    def create_via_page(self):
        f = tb.Frame(self.content)
        self.frames["Via Recommendation"] = f
        group = tb.Labelframe(f, text="Input", bootstyle="info", padding=(12,8))
        group.pack(side="left", fill="y", pady=30, padx=30)
        vcmd = (self.register(validate_float), '%P')
        self.via_vars = [tb.StringVar(value="1"), tb.StringVar(value="1.6"), tb.StringVar(value="25"),
                         tb.StringVar(value="20"), tb.StringVar(value="1")]
        labels = ["Via Current", "PCB Thickness", "Plating", "Temp Rise", "Parallel Vias"]
        units = ["A", "mm", "μm", "°C", ""]
        hints = [
            "Current to handle per via.",
            "Thickness of the PCB.",
            "Electroplated copper thickness in via barrel.",
            "Maximum allowed temperature rise.",
            "How many vias used in parallel."
        ]
        for i, (lbl, unit) in enumerate(zip(labels, units)):
            tb.Label(group, text=f"{lbl}:", font=("Segoe UI",11)).grid(row=i,column=0,sticky="e",pady=4)
            e = tb.Entry(group, textvariable=self.via_vars[i], width=10, validate='key', validatecommand=vcmd)
            e.grid(row=i,column=1,sticky="ew",padx=2)
            tb.Label(group, text=unit, width=6, anchor="w",font=("Segoe UI", 11), foreground="#7C7C8B"
                ).grid(row=i,column=2,sticky="w")
            ToolTip(e, hints[i])
        calcbtn = tb.Button(group, text="Calculate", bootstyle="success", command=self.calc_via)
        ToolTip(calcbtn, "Calculate all via options for these constraints.")
        calcbtn.grid(row=6, column=0, columnspan=3, pady=10)
        resplot = tb.Labelframe(f, text="Recommendation & Plot", bootstyle="info", padding=(8,8))
        resplot.pack(side="left", fill="both", expand=True, pady=30, padx=(0,30))
        self.via_table = tb.Treeview(resplot, columns=("Dia", "Pad", "Cap", "AR", "✔"), show='headings', height=7,bootstyle="info")
        for col in ("Dia","Pad","Cap","AR","✔"):
            self.via_table.heading(col, text=col)
            self.via_table.column(col, width=78 if col!="✔" else 35, anchor="center")
        self.via_table.pack(padx=5, pady=2)
        self.via_fig = plt.Figure(figsize=(3.6,3.2), dpi=90)
        self.via_ax = self.via_fig.add_subplot(111)
        self.via_canvas = FigureCanvasTkAgg(self.via_fig, master=resplot)
        self.via_canvas.get_tk_widget().pack(anchor="nw", pady=7)
        
    def calc_via(self):
        vals = [float(v.get()) for v in self.via_vars]
        table = PCBModel.via_recommend(*vals)
        for r in self.via_table.get_children(): self.via_table.delete(r)
        for row in table: self.via_table.insert("", "end", values=row)
        self.via_ax.clear()
        diameters = [0.2, 0.25, 0.3, 0.4, 0.5, 0.6, 0.8]
        n_vias = vals[4]
        amps = []
        for d in diameters:
            t_mm = vals[2] / 1000.0
            out_d = d + 2 * t_mm
            area_mm2 = math.pi * ((out_d/2)**2 - (d/2)**2)
            resistance = 1.68e-8 * (vals[1] / 1000) / (area_mm2 * 1e-6)
            ampacity = math.sqrt(vals[3] / (resistance * 0.024))
            amps.append(ampacity * n_vias)
        self.via_ax.plot(diameters, amps, 'o-', color="#34fa62", linewidth=2)
        self.via_ax.axhline(vals[0], color="#fc686c", linestyle="--", label="Required")
        self.via_ax.set_xlabel("Via Diameter (mm)")
        self.via_ax.set_ylabel("Max Current (A)")
        self.via_ax.set_title("Via Ampacity vs Diameter", fontsize=10)
        self.via_ax.grid(True)
        self.via_ax.legend()
        self.via_canvas.draw()
        self.calc_results["via"] = self.via_table
        self.update_recommendation()

    def create_imp_page(self):
        f = tb.Frame(self.content)
        self.frames["Impedance"] = f
        group = tb.Labelframe(f, text="Inputs", bootstyle="info", padding=(10,8))
        group.pack(side="left", fill="y", pady=30, padx=30)
        vcmd = (self.register(validate_float), '%P')
        self.imp_vars = [tb.StringVar(value="0.25"), tb.StringVar(value="0.18"), tb.StringVar(value="0.035"),
                         tb.StringVar(value="FR-4 (4.4)")]
        labels = ["Trace Width", "Height to Plane", "Cu Thickness", "Material"]
        units = ["mm", "mm", "mm", ""]
        hints = [
            "Width of the microstrip trace.",
            "Height from trace to reference plane below.",
            "Copper thickness of trace.",
            "Board dielectric material and εr value."
        ]
        for i, (lbl, unit) in enumerate(zip(labels[:-1], units[:-1])):
            tb.Label(group, text=f"{lbl}:", font=("Segoe UI",11)).grid(row=i,column=0,sticky="e",pady=5)
            e = tb.Entry(group, textvariable=self.imp_vars[i], width=10, validate='key', validatecommand=vcmd)
            e.grid(row=i,column=1,sticky="ew",padx=2)
            tb.Label(group, text=unit, width=5, anchor="w",font=("Segoe UI",10),foreground="#7C7C8B"
                    ).grid(row=i,column=2,sticky="w")
            ToolTip(e, hints[i])
        tb.Label(group, text="Material ", font=("Segoe UI",11)).grid(row=3,column=0,sticky="e",pady=2)
        matbox = tb.Combobox(group, textvariable=self.imp_vars[3], values=[f"{n} ({v})" for n,v in self.materials.items()],
                             state="readonly", width=16)
        matbox.set("FR-4 (4.4)"); matbox.grid(row=3,column=1,columnspan=2,sticky="ew")
        ToolTip(matbox, hints[3])
        calcbtn = tb.Button(group,text="Calculate",bootstyle="success", command=self.calc_imp)
        ToolTip(calcbtn, "Calculate Z0 for set geometry and board material.")
        calcbtn.grid(row=4, column=0, columnspan=3, pady=12)
        result_box = tb.Text(f, height=5, width=54, font=("Consolas", 12), state="disabled")
        result_box.pack(side="top", padx=12, pady=12, anchor="w")
        self.imp_res = result_box

        self.imp_fig = plt.Figure(figsize=(3.8,3.2), dpi=90)
        self.imp_ax = self.imp_fig.add_subplot(111)
        self.imp_canvas = FigureCanvasTkAgg(self.imp_fig, master=f)
        self.imp_canvas.get_tk_widget().pack(anchor="nw", pady=6)
        
    def calc_imp(self):
        w = float(self.imp_vars[0].get())
        h = float(self.imp_vars[1].get())
        t = float(self.imp_vars[2].get())
        er = float(self.imp_vars[3].get().split("(")[1].split(")")[0])
        z0 = PCBModel.impedance_microstrip(w, h, t, er)
        self.imp_res.config(state='normal')
        self.imp_res.delete("1.0","end")
        self.imp_res.insert("end", f"Impedance: {z0:.2f} Ω (Hammerstad/Jensen)\n")
        self.imp_res.config(state='disabled')
        self.imp_ax.clear()
        widths = [x*0.02 for x in range(2,41)]
        Z = [PCBModel.impedance_microstrip(x, h, t, er) for x in widths]
        self.imp_ax.plot(widths, Z, '-', lw=2,color="#0984FF")
        self.imp_ax.axvline(w, color="#FF6C26", ls="--",label="Current Width")
        self.imp_ax.set_xlabel("Width (mm)"); self.imp_ax.set_ylabel("Z0 (Ω)")
        self.imp_ax.set_title("Microstrip Impedance vs Width", fontsize=10)
        self.imp_ax.grid(True); self.imp_ax.legend()
        self.imp_canvas.draw()
        self.calc_results["impedance"] = self.imp_res
        self.update_recommendation()

    def create_vdrop_page(self):
        f = tb.Frame(self.content)
        self.frames["Voltage Drop"] = f
        group = tb.Labelframe(f, text="Inputs", bootstyle="info", padding=(10,8))
        group.pack(side="left", fill="y", pady=20, padx=22)
        vcmd = (self.register(validate_float), '%P')
        self.vd_vars = [tb.StringVar(value="0.5"), tb.StringVar(value="50"), tb.StringVar(value="35"), tb.StringVar(value="2")]
        labels = ["Trace Width", "Length", "Copper", "Current"]
        units = ["mm","mm","μm","A"]
        hints = [
            "Trace width in mm.",
            "Trace length in mm.",
            "Copper thickness in μm (35μm = 1oz).",
            "Current through the trace."
        ]
        for i, (lbl, unit) in enumerate(zip(labels, units)):
            tb.Label(group, text=f"{lbl}:", font=("Segoe UI",11)).grid(row=i,column=0,sticky="e",pady=2)
            e = tb.Entry(group, textvariable=self.vd_vars[i], width=10, validate='key', validatecommand=vcmd)
            e.grid(row=i,column=1,sticky="ew",padx=2)
            tb.Label(group, text=unit, width=5, anchor="w",font=("Segoe UI", 11),foreground="#7C7C8B"
                    ).grid(row=i,column=2,sticky="w")
            ToolTip(e, hints[i])
        calcbtn = tb.Button(group,text="Calculate",bootstyle="success", command=self.calc_vdrop)
        ToolTip(calcbtn, "Calculate trace voltage drop and power dissipation.")
        calcbtn.grid(row=4, column=0, columnspan=3, pady=10)
        result_box = tb.Text(f, height=5, width=54, font=("Consolas", 12), state="disabled")
        result_box.pack(side="top", padx=12, pady=22)
        self.vdrop_res = result_box

    def calc_vdrop(self):
        w, l, cu, i = [float(v.get()) for v in self.vd_vars]
        r, v, p = PCBModel.voltage_drop(w, cu, l, i)
        self.vdrop_res.config(state="normal")
        self.vdrop_res.delete("1.0","end")
        self.vdrop_res.insert("end", f"Resistance: {r:.5f} Ω\nVoltage drop: {v:.4f} V\nPower loss: {p*1000:.2f} mW\n")
        self.vdrop_res.config(state="disabled")
        self.calc_results["vdrop"] = self.vdrop_res
        self.update_recommendation()

    def create_clearance_page(self):
        f = tb.Frame(self.content)
        self.frames["Clearance"] = f
        group = tb.Labelframe(f, text="Parameters", bootstyle="info", padding=(10,8))
        group.pack(side="left", fill="y", padx=20, pady=28)
        vcmd = (self.register(validate_float), '%P')
        self.clr_var1 = tb.StringVar(value="60")
        tb.Label(group, text="Voltage (V):", font=("Segoe UI", 11)).grid(row=0,column=0,sticky="e",pady=3)
        ent = tb.Entry(group, textvariable=self.clr_var1, width=12, validate='key', validatecommand=vcmd)
        ent.grid(row=0,column=1,padx=3)
        ToolTip(ent, "Enter maximum voltage between conductors.")
        tb.Label(group, text="Location:", font=("Segoe UI", 11)).grid(row=1,column=0,sticky="e",pady=3)
        self.clr_loc = tb.StringVar(value="external_uncoated")
        opts=[("Internal","internal"),("External Uncoated","external_uncoated"),("External Coated","external_coated")]
        comb = tb.Combobox(group, textvariable=self.clr_loc, values=[o[0] for o in opts], state="readonly", width=19)
        comb.grid(row=1,column=1,padx=3)
        ToolTip(comb, "Where on the board is the clearance measured?")
        calcbox = tb.Labelframe(f, text="Clearance Result", bootstyle="info", padding=(10,8))
        calcbox.pack(side="left", fill="both",expand=True,padx=(8,0),pady=28)
        self.clr_result = tb.Text(calcbox, height=4, width=54, font=("Consolas", 12),state='disabled')
        self.clr_result.pack(side="left",anchor="n")
        calc_btn = tb.Button(group, text="Calculate", bootstyle="success", width=14, command=self.calc_clearance)
        calc_btn.grid(row=2,column=0,columnspan=2,pady=16)
        ToolTip(calc_btn, "Check minimum required clearance (IPC-2221B).")

    def calc_clearance(self):
        v = float(self.clr_var1.get())
        locval = self.clr_loc.get()
        opts=[("Internal","internal"),("External Uncoated","external_uncoated"),("External Coated","external_coated")]
        loc = [l for n,l in opts if n==locval][0]
        val = PCBModel.clearance_ipc2221(v, loc)
        self.clr_result.config(state="normal")
        self.clr_result.delete("1.0","end")
        self.clr_result.insert("end", f"Minimum clearance: {val:.3f} mm (IPC-2221B)\n")
        self.clr_result.config(state="disabled")
        self.calc_results["clearance"] = self.clr_result
        self.update_recommendation()

    def create_scenario_page(self):
        f = tb.Frame(self.content)
        self.frames["Best Scenario"] = f
        tb.Label(f, text="Best Possible Engineering Scenario", font=("Segoe UI", 15, "bold"),
                 foreground="#10FFCC", background="#232B2B").pack(pady=20)
        self.recommend_box = tk.Text(f, height=14, width=105, bg="#232B2B", fg="#D0FFB4", font=("Consolas", 12))
        self.recommend_box.pack(pady=14)

    def update_recommendation(self):
        suggestions = []
        try:
            val = self.trace_res.get("1.0","end").strip()
            if val:
                w = float(val.split(":")[1].split("mm")[0])
                if w < 0.2:
                    suggestions.append("⚡ Trace width is quite thin (<0.2mm). Increase copper thickness or reduce current.")
                elif w > 2:
                    suggestions.append("🧱 Trace width large — use pour or increase copper for compactness.")
                else:
                    suggestions.append("✅ Trace width is optimal for target current/thermal rise.")
        except: pass
        try:
            table = self.via_table
            rows = [table.item(i)['values'] for i in table.get_children()]
            best = [r for r in rows if r[-1] == "✔"]
            if best:
                d = best[0][0]
                suggestions.append(f"🕳 Recommended via diameter: {d} mm (adequate current capacity).")
            else:
                suggestions.append("❌ No via meets required ampacity — increase via count or diameter.")
        except: pass
        try:
            val = self.imp_res.get("1.0","end").strip()
            if val:
                z = float(val.split(":")[1].split("Ω")[0])
                if abs(z-50)<2:
                    suggestions.append("✅ Trace impedance very close to 50Ω — ideal for most RF/high-speed signals.")
                elif z>60:
                    suggestions.append("⚠️  Impedance too high; reduce width or raise εr.")
                else:
                    suggestions.append("⚠️  Impedance low; increase width or reduce εr.")
        except: pass
        try:
            val = self.vdrop_res.get("1.0","end").strip()
            if val:
                parts = val.split("\n")
                vdrop = float(parts[1].split(":")[1].replace("V",""))
                if vdrop > 0.2:
                    suggestions.append(f"⚡ Voltage drop is noticeable ({vdrop:.3f} V) — consider shorter trace or wider width.")
        except: pass
        try:
            val = self.clr_result.get("1.0","end").strip()
            if val:
                v = float(self.clr_var1.get())
                c = float(val.split(":")[1].split("mm")[0])
                if c > 3:
                    suggestions.append(f"🛡 High-voltage (>250V): ensure creepage is also met.")
                else:
                    suggestions.append(f"✅ Clearance {c:.2f} mm set for {v:.0f}V per IPC-2221B.")
        except: pass
        sstr = "\n".join(suggestions)
        try:
            self.recommend_box.delete("1.0","end")
            self.recommend_box.insert("end",sstr)
        except:
            pass

    def export_results(self):
        alltext = ""
        for k, widget in self.calc_results.items():
            alltext += f"\n{'='*40}\n--- {k.upper()} ---\n{'='*40}\n"
            if isinstance(widget, tb.Text) or isinstance(widget, tk.Text):
                alltext += widget.get(1.0, "end")
            elif isinstance(widget, tb.Treeview):
                colnames = [widget.heading(c)['text'] for c in widget["columns"]]
                alltext += ", ".join(colnames) + "\n"
                for row in widget.get_children():
                    vals = widget.item(row)['values']
                    alltext += ", ".join(str(v) for v in vals) + "\n"
        file = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text file","*.txt")])
        if file:
            with open(file, "w") as f:
                f.write(alltext)
            messagebox.showinfo("Export", f"Results exported to:\n{file}")

if __name__ == "__main__":
    PCBToolkitGUI().mainloop() 
