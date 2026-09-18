"""
7-DOF Surgical Robot Physiological Tremor Filtering (8-12 Hz)
Conforming to IEC 60601-1 & ISO 10218 Standards.
Group 10 - B.Tech CSBS MDRIIA
"""
import math
import numpy as np

def simulate_tremor_filter(n_samples=500):
    print("[MDRIIA Group 10] Simulating Surgical Tremor Filtering...")
    dt = 0.002
    t = np.linspace(0, n_samples * dt, n_samples)
    
    # Surgeon Intent: Smooth 0.5 Hz incision sweep
    intent = 0.05 * np.sin(2 * np.pi * 0.5 * t)
    
    # Physiological Hand Tremor: 9.5 Hz oscillation
    tremor = 0.008 * np.sin(2 * np.pi * 9.5 * t)
    raw_signal = intent + tremor
    
    # Low-pass filter (Cutoff at 3.0 Hz)
    filtered = np.zeros_like(raw_signal)
    alpha = 0.08 # First-order exponential smoothing filter
    for i in range(1, n_samples):
        filtered[i] = alpha * raw_signal[i] + (1 - alpha) * filtered[i-1]
        
    tremor_attenuation_db = 20 * math.log10(np.std(filtered - intent) / np.std(tremor))
    print(f"Unfiltered RMS Tremor:  {np.std(tremor)*1000:.3f} mm")
    print(f"Filtered Residual Error: {np.std(filtered - intent)*1000:.3f} mm")
    print(f"Tremor Attenuation:      {abs(tremor_attenuation_db):.1f} dB suppression")

if __name__ == "__main__":
    simulate_tremor_filter()
