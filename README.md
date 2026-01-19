# PCBLy Toolkit 🛠️ (PCB Engineering GUI)

**PCBLy Toolkit** is a Python-based desktop GUI application built to assist PCB designers and electronics engineers with common PCB calculations such as **trace width**, **via current capacity**, **microstrip impedance**, **voltage drop**, and **clearance rules**.

This project is designed to be a lightweight “PCB design sidekick” for quick engineering checks during schematic and PCB layout work.

---

## ✨ Features

✅ **Trace Width Calculator (IPC-2152 inspired)**  
- Calculates recommended minimum trace width based on:
  - Current (A)
  - Copper thickness (µm)
  - Allowed temperature rise (°C)
  - External / internal layer option

✅ **Via Recommendation Tool**
- Suggests practical via sizes based on:
  - Current requirement
  - PCB thickness
  - Plating thickness
  - Temperature rise
  - Number of parallel vias  
- Includes an “OK ✔” flag for valid via options

✅ **Microstrip Impedance Calculator**
- Estimates characteristic impedance for a microstrip line based on:
  - Trace width (mm)
  - Height to reference plane (mm)
  - Copper thickness (mm)
  - Dielectric material (εr)

✅ **Voltage Drop & Power Loss**
- Calculates:
  - Trace resistance (Ω)
  - Voltage drop (V)
  - Power loss (mW)

✅ **Clearance Calculator (IPC-2221 inspired)**
- Estimates minimum clearance requirement based on:
  - Voltage
  - PCB location type:
    - internal
    - external (coated / uncoated)

✅ **Best Scenario Summary**
- Generates simplified engineering recommendations based on the results of the calculations.

✅ **Export Results**
- Exports all calculated outputs into a `.txt` report file for documentation/reference.

---

## 🖥️ Screenshots (Recommended)
Add screenshots to a folder like:

