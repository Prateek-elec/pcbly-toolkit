# PCBly 🛠️

A lightweight PCB Engineering Toolkit GUI built using **Python + Tkinter + ttkbootstrap**.

It helps you quickly calculate important PCB design parameters like:
- Trace width (IPC-2152)
- Via recommendation + ampacity plotting
- Microstrip impedance (Hammerstad/Jensen)
- Voltage drop + power loss
- Clearance (IPC-2221B)
- Best Scenario recommendation based on results

---

## ✨ Features
✅ Clean multi-page GUI  
✅ Tooltip-based guidance for inputs  
✅ Interactive plots using Matplotlib  
✅ Export report feature  

---

## 📌 Tools Included

### 1. Trace Width Calculator (IPC-2152)
Calculates minimum required trace width based on:
- Current
- Copper thickness
- Allowed temperature rise
- External/Internal layer option

### 2. Via Recommendation Tool
Finds suitable via diameter & pad sizes based on:
- Via current
- PCB thickness
- Plating thickness
- Temperature rise
- Number of parallel vias

### 3. Impedance Calculator (Microstrip)
Calculates approximate microstrip impedance using Hammerstad/Jensen model.

### 4. Voltage Drop Calculator
Returns:
- Resistance
- Voltage drop
- Power loss

### 5. Clearance Calculator (IPC-2221B)
Returns minimum clearance required for a given voltage and board condition.

### 6. Best Scenario Page
Gives engineering suggestions based on your calculated results.

---

## 🖥️ Screenshot
(Add your screenshot inside `assets/screenshots/`)

---

## 🚀 How to Run

### Install dependencies
```bash
pip install -r requirements.txt

