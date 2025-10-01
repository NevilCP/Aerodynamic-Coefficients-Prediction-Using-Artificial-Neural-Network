#!/usr/bin/env python3
"""
master_generate_airfoil_dataset.py

This script generates a comprehensive dataset of NACA 4-digit airfoil aerodynamic
and geometric data. It systematically varies airfoil parameters (max camber,
camber location, thickness), flow conditions (Reynolds number, Mach number),
and angle of attack.

The script automates the process by:
1.  Generating JavaFoil macro files for each unique parameter combination.
2.  Executing JavaFoil in parallel across multiple CPU cores to perform the
    aerodynamic analysis.
3.  Parsing the resulting XML output files from JavaFoil.
4.  Calculating the airfoil's y-coordinates at cosine-spaced points.
5.  Aggregating all data into a single, wide-format CSV file with a
    progress bar.

The final CSV contains one row for each angle of attack, with columns for
the airfoil parameters, flow conditions, aerodynamic coefficients (CL, CD, Cm),
and the upper and lower surface y-coordinates.
"""

import math
import subprocess
import time
import csv
from pathlib import Path
import xml.etree.ElementTree as ET
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import List, Tuple, Optional
from itertools import product
from functools import lru_cache
from tqdm import tqdm

# ==============================================================================
# USER CONFIGURATION
# ==============================================================================

# --- JavaFoil Paths ---
# Ensure these paths are correct for your system.
JAVA_BIN = "/usr/lib/jvm/java-8-openjdk-amd64/jre/bin/java"
JAVAFOIL_JAR = "/home/nevilcp/MH-AeroTools/JavaFoil/javafoil.jar"
MHCLASSES_JAR = "/home/nevilcp/MH-AeroTools/JavaFoil/mhclasses.jar"

# --- Directory and File Paths ---
# Defines where temporary files and final results will be stored.
BASE_DIR = Path.home() / "ML_Aero"
MACRO_TEMP_DIR = BASE_DIR / "macros_temp"
RESULTS_DIR = BASE_DIR / "results"
MASTER_CSV_PATH = RESULTS_DIR / "master_airfoil_dataset.csv"

# --- Airfoil NACA 4-Digit Parameter Sweeps ---
# Defines the range of airfoil shapes to be generated.
MAX_CAMBER_LIST = list(range(0, 10))     # Max camber (m) in percent chord (0% to 9%)
CAMBER_LOC_LIST = list(range(10, 71, 10)) # Camber location (p) in tenths of chord (10% to 70%)
THICKNESS_LIST = list(range(5, 36, 5))   # Max thickness (t) in percent chord (5% to 35%)

# --- Flow Condition Sweeps ---
# Defines the Reynolds and Mach numbers for the analysis.
REYNOLDS_LIST = [1e5, 2e5, 3e5, 4e5, 5e5]
MACH_LIST = [0.1, 0.2, 0.3]

# --- Angle of Attack (AoA) Sweep ---
# Defines the range of angles for the aerodynamic polar.
AOA_START = -10.0
AOA_END = 10.0
AOA_STEP = 1.0

# --- Geometry and Simulation Settings ---
# Defines the precision of the airfoil coordinates and other settings.
NUM_COORDINATE_POINTS = 101  # Number of cosine-spaced points for geometry
POST_RUN_WAIT_S = 0.1        # Small delay (in seconds) after each JavaFoil run
CSV_WRITE_BATCH_SIZE = 500   # Number of rows to buffer in memory before writing to disk

# ==============================================================================
# JAVAFOIL MACRO TEMPLATE
# ==============================================================================

MACRO_TEMPLATE = """// JavaFoil auto-generated macro
Options.Country(1);
Geometry.CreateAirfoil(0, {n_points}, {thickness_frac}, 0.0, {max_camber_frac}, {camber_loc_frac}, 0.0, 0.0, 0.0, 0.0, 1);
Options.MachNumber({mach});
Polar.Analyze({re}, {re}, {re}, {aoa_start}, {aoa_end}, {aoa_step}, 1.0, 1.0, 0, false);
Polar.Save("{output_path}");
JavaFoil.Exit();
"""

# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def run_javafoil_macro(macro_path: Path) -> Tuple[int, str, str]:
    """Executes a JavaFoil macro script using a subprocess."""
    command = [
        JAVA_BIN,
        "-cp", str(MHCLASSES_JAR),
        "-jar", str(JAVAFOIL_JAR),
        f"Script={str(macro_path)}"
    ]
    process = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding='utf-8'
    )
    return process.returncode, process.stdout, process.stderr

def get_cosine_spaced_points(num_points: int) -> List[float]:
    """Generates a list of x-coordinates with cosine spacing."""
    return [0.5 * (1 - math.cos(math.pi * i / (num_points - 1))) for i in range(num_points)]

@lru_cache(maxsize=1024)
def calculate_naca_4digit_coords(
    max_camber: int, camber_loc: int, thickness: int, num_points: int
) -> Tuple[List[float], List[float]]:
    """
    Calculates the upper and lower surface y-coordinates for a NACA 4-digit airfoil.
    Uses an LRU cache to avoid re-calculating geometry for the same airfoil.
    Excludes the leading (0,0) and trailing edge points.
    """
    m = max_camber / 100.0
    p = camber_loc / 10.0
    t = thickness / 100.0
    x_coords = get_cosine_spaced_points(num_points)

    y_upper_coords, y_lower_coords = [], []

    for x in x_coords:
        # Thickness distribution
        yt = 5.0 * t * (
            0.2969 * math.sqrt(x) - 0.1260 * x - 0.3516 * x**2 +
            0.2843 * x**3 - 0.1015 * x**4
        )

        # Camber line and gradient
        if m == 0.0 or p == 0.0:
            yc, dyc_dx = 0.0, 0.0
        elif x < p:
            yc = (m / (p**2)) * (2 * p * x - x**2)
            dyc_dx = (2 * m / (p**2)) * (p - x)
        else:
            yc = (m / ((1 - p)**2)) * ((1 - 2 * p) + 2 * p * x - x**2)
            dyc_dx = (2 * m / ((1 - p)**2)) * (p - x)

        theta = math.atan(dyc_dx)

        # Final surface coordinates
        y_upper = yc + yt * math.cos(theta)
        y_lower = yc - yt * math.cos(theta)
        y_upper_coords.append(y_upper)
        y_lower_coords.append(y_lower)

    # Exclude endpoints (index 0 and -1) which are typically (0,0)
    return y_upper_coords[1:-1], y_lower_coords[1:-1]

def parse_javafoil_xml(xml_path: Path) -> List[Tuple[float, float, float, float]]:
    """Parses the JavaFoil XML output file to extract aerodynamic coefficients."""
    try:
        tree = ET.parse(str(xml_path))
        root = tree.getroot()
        namespace = {'ns': "http://www.mh-aerotools.de/polar-schema"}
        polar = root.find('.//ns:polar', namespace)
        if polar is None:
            return []

        # Get variable names to correctly index columns
        var_nodes = polar.findall('.//ns:variables/ns:variable', namespace)
        var_names = [v.text.strip().lower() for v in var_nodes]
        idx = {name: var_names.index(name) for name in var_names}

        # Extract data points
        data_rows = []
        dp_nodes = polar.findall('.//ns:datapoints/ns:datapoint', namespace)
        for dp in dp_nodes:
            vals = [v.text.strip().replace(',', '.') for v in dp.findall('ns:value', namespace)]
            def get_val(name):
                return float(vals[idx[name]]) if name in idx and idx[name] < len(vals) else 0.0
            
            row = (get_val('alpha'), get_val('cl'), get_val('cd'), get_val('cm'))
            data_rows.append(row)
        return data_rows
    except (ET.ParseError, FileNotFoundError, IndexError):
        return []

# ==============================================================================
# MAIN WORKER FUNCTION
# ==============================================================================

def process_airfoil_case(params: tuple) -> Optional[List[list]]:
    """
    Generates and runs a single airfoil case, returning data rows for the CSV.
    This function is executed by each parallel worker.
    """
    max_camber, camber_loc, thickness, reynolds, mach = params
    
    # --- MODIFIED SECTION START ---
    # Correctly format the NACA 4-digit airfoil name.
    # The second digit is the camber location in tenths of chord (p/10).
    p_digit = camber_loc // 10
    airfoil_name = f"NACA{max_camber}{p_digit}{str(thickness).zfill(2)}"
    # --- MODIFIED SECTION END ---
    
    # Define file paths
    file_prefix = f"{airfoil_name}_Re{int(reynolds)}_M{str(mach).replace('.', 'p')}"
    xml_output_path = RESULTS_DIR / f"{file_prefix}_polar.xml"
    macro_file_path = MACRO_TEMP_DIR / f"macro_{file_prefix}.js"

    # Generate the JavaFoil macro script
    macro_text = MACRO_TEMPLATE.format(
        n_points=NUM_COORDINATE_POINTS,
        max_camber_frac=max_camber / 100.0,
        camber_loc_frac=camber_loc / 10.0,
        thickness_frac=thickness / 100.0,
        mach=mach,
        re=int(reynolds),
        aoa_start=AOA_START,
        aoa_end=AOA_END,
        aoa_step=AOA_STEP,
        output_path=str(xml_output_path)
    )
    macro_file_path.write_text(macro_text, encoding='utf-8')

    # Run JavaFoil
    if xml_output_path.exists():
        xml_output_path.unlink()
    
    return_code, _, stderr = run_javafoil_macro(macro_file_path)
    time.sleep(POST_RUN_WAIT_S)

    if return_code != 0 or not xml_output_path.exists():
        if stderr and stderr.strip():
            # Use tqdm.write to print messages without breaking the progress bar
            tqdm.write(f"Warning: JavaFoil failed for {file_prefix}. Error: {stderr.strip()}")
        return None

    # Parse results and generate coordinates
    polar_data = parse_javafoil_xml(xml_output_path)
    if not polar_data:
        return None

    y_upper, y_lower = calculate_naca_4digit_coords(
        max_camber, camber_loc, thickness, NUM_COORDINATE_POINTS
    )

    # Combine all data into rows for the final CSV
    csv_rows = []
    for alpha, cl, cd, cm in polar_data:
        base_row = [
            airfoil_name, max_camber, camber_loc, thickness,
            alpha, mach, int(reynolds), cl, cd, cm
        ]
        full_row = base_row + y_upper + y_lower
        csv_rows.append(full_row)
        
    return csv_rows

# ==============================================================================
# SCRIPT ENTRY POINT
# ==============================================================================

def main():
    """Main routine to set up, execute, and save the dataset."""
    print("Starting airfoil dataset generation...")
    
    # Create necessary directories
    MACRO_TEMP_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Temporary macros will be stored in: {MACRO_TEMP_DIR}")
    print(f"Results will be saved in: {RESULTS_DIR}")

    # --- Prepare CSV Header ---
    num_geom_points = NUM_COORDINATE_POINTS - 2  # Excludes endpoints
    geom_cols = (
        [f"yU{k}" for k in range(1, num_geom_points + 1)] +
        [f"yL{k}" for k in range(1, num_geom_points + 1)]
    )
    header = ['FoilID', 'm', 'p', 't', 'Alpha', 'M', 'Re', 'CL', 'CD', 'Cm'] + geom_cols

    # --- Write CSV Header ---
    with MASTER_CSV_PATH.open('w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(header)

    # --- Generate All Parameter Combinations ---
    param_lists = [
        MAX_CAMBER_LIST, CAMBER_LOC_LIST, THICKNESS_LIST,
        REYNOLDS_LIST, MACH_LIST
    ]
    all_params = list(product(*param_lists))
    print(f"Generated {len(all_params)} unique parameter combinations to process.")

    # --- Run Simulations in Parallel ---
    results_batch = []
    with ProcessPoolExecutor() as executor:
        futures = [executor.submit(process_airfoil_case, p) for p in all_params]
        
        pbar = tqdm(as_completed(futures), total=len(futures), desc="Generating Airfoils")
        for future in pbar:
            result_rows = future.result()
            if result_rows:
                results_batch.extend(result_rows)
                # When the batch is full, write it to the CSV file
                if len(results_batch) >= CSV_WRITE_BATCH_SIZE:
                    with MASTER_CSV_PATH.open('a', newline='', encoding='utf-8') as f:
                        writer = csv.writer(f)
                        writer.writerows(results_batch)
                    results_batch.clear()  # Clear the batch after writing

    # Write any remaining results from the last batch
    if results_batch:
        with MASTER_CSV_PATH.open('a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerows(results_batch)


    print("\n" + "="*50)
    print("Dataset generation complete!")
    print(f"Master dataset has been saved to: {MASTER_CSV_PATH}")
    print("="*50)

if __name__ == '__main__':
    main()


