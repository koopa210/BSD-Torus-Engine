import multiprocessing as mp
import time
import sys
import argparse
import math
import random

def get_primes(n):
    # Sieve of Eratosthenes cache for quick L-function proxy
    primes = []
    is_prime = [True] * (n + 1)
    for p in range(2, n + 1):
        if is_prime[p]:
            primes.append(p)
            for i in range(p * p, n + 1, p):
                is_prime[i] = False
    return primes

PRIMES = get_primes(500)

def calc_ap(a, b, p):
    # Modulo p counting for Hasse-Weil defect (a_p)
    points = 1 # Identity (Infinity) counts as 1
    for x in range(p):
        rhs = (pow(x, 3, p) + a*x + b) % p
        if rhs == 0:
            points += 1
        elif pow(rhs, (p-1)//2, p) == 1:
            points += 2
    return (p + 1) - points

def evaluate_l_function_proxy(a, b):
    # Heuristic limit summation for L(1). 
    # If the wave flatlines around 0.0 or positive, the curve likely generates infinite points.
    l_sum = 0
    for p in PRIMES[:50]:
        ap = calc_ap(a, b, p)
        l_sum += ap / p
    return l_sum

# ----------------------------------------------------
# JACOBIAN INTEGER ARITHMETIC (Zero Floating Point Loss)
# ----------------------------------------------------
def double_point(X, Y, Z, a):
    if Y == 0 or Z == 0:
        return 0, 0, 0
    Y_sq = Y * Y
    S = 4 * X * Y_sq
    Z_sq = Z * Z
    M = 3 * X * X + a * Z_sq * Z_sq
    X_prime = M * M - 2 * S
    Y_prime = M * (S - X_prime) - 8 * Y_sq * Y_sq
    Z_prime = 2 * Y * Z
    return X_prime, Y_prime, Z_prime

def add_points(X1, Y1, Z1, X2, Y2, Z2, a):
    if Z1 == 0: return X2, Y2, Z2
    if Z2 == 0: return X1, Y1, Z1
    Z1_sq = Z1 * Z1
    Z2_sq = Z2 * Z2
    U1 = X1 * Z2_sq
    U2 = X2 * Z1_sq
    S1 = Y1 * Z2_sq * Z2
    S2 = Y2 * Z1_sq * Z1
    
    if U1 == U2:
        if S1 != S2: return 0, 0, 0 
        return double_point(X1, Y1, Z1, a)
        
    H = U2 - U1
    R = S2 - S1
    H_sq = H * H
    H_cb = H_sq * H
    
    X3 = R * R - H_cb - 2 * U1 * H_sq
    Y3 = R * (U1 * H_sq - X3) - S1 * H_cb
    Z3 = H * Z1 * Z2
    return X3, Y3, Z3

def multiply_point(k, X, Y, Z, a):
    # Binary double-and-add execution
    RX, RY, RZ = 0, 0, 0 # Starts at Infinity
    BX, BY, BZ = X, Y, Z
    while k > 0:
        if k % 2 == 1:
            RX, RY, RZ = add_points(RX, RY, RZ, BX, BY, BZ, a)
        BX, BY, BZ = double_point(BX, BY, BZ, a)
        k //= 2
    return RX, RY, RZ

def hunt_curve_batch(worker_id, verbose):
    curves_checked = 0
    anomalies_found = 0
    
    while True:
        a = random.randint(-5000, 5000)
        b = random.randint(-5000, 5000)
        delta = -16 * (4*(a**3) + 27*(b**2))
        if delta == 0: continue
        
        # 1. Filter Check (L-Wave Predicts Infinite Status)
        l_wave = evaluate_l_function_proxy(a, b)
        if abs(l_wave) > 0.8:
            # Rank 0 (Torsion Trap predicted) -> Skip finding generator
            curves_checked += 1
            continue
            
        # 2. Likely Infinity (Rank 1+) -> Search for Seed Integer
        gen_x, gen_y = None, None
        for x in range(-50, 100):
            rhs = x*x*x + a*x + b
            if rhs >= 0:
                y_approx = math.isqrt(rhs)
                if y_approx * y_approx == rhs and y_approx > 0:
                    gen_x, gen_y = x, y_approx
                    break
        
        if not gen_x:
            curves_checked += 1
            continue
            
        # 3. Mazur's Boundary Strike (17 P)
        X, Y, Z = gen_x, gen_y, 1
        HX, HY, HZ = multiply_point(17, X, Y, Z, a)
        
        if HZ == 0:
            # [ANOMALY] The point perfectly looped back into Torsion (0) despite L-wave predicting infinity
            anomalies_found += 1
            if verbose:
                msg = f"\033[91m[ANOMALY BREACH!]\033[0m y^2 = x^3 + {a}x + {b} | Loop Collapsed at 17P | L-Wave: {l_wave:.2f}\n"
                sys.stdout.write(msg)
                sys.stdout.flush()
        else:
            if verbose:
                color = "\033[92m" if random.random() > 0.2 else "\033[96m"
                z_len = len(str(HZ))
                x_len = len(str(HX))
                msg = f"{color}[INFINITE]{chr(27)}[0m y^2 = x^3 + {a}x + {b} | 17P Hit | Z-Width: {z_len} digits | X-Width: {x_len} digits\n"
                sys.stdout.write(msg)
                sys.stdout.flush()
        
        curves_checked += 1
        if not verbose and curves_checked % 500 == 0:
            sys.stdout.write(f"Worker {worker_id} passed {curves_checked} Elliptic Checks... (Anomalies: {anomalies_found})\n")
            sys.stdout.flush()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Strix Halo BSD Counter-Example Hunter")
    parser.add_argument('--matrix', action='store_true', help='Enable Matrix telemetry stream (Warning: CPU intense I/O)')
    parser.add_argument('--cores', type=int, default=mp.cpu_count(), help='Core override limit')
    args = parser.parse_args()
    
    print(f"==================================================")
    print(f"| BSD TORUS ENGINE: STRIX HALO COMPUTE MATRIX    |")
    print(f"==================================================")
    # Clamp cores for safety on script starts unless maxed explicitly, 
    # but mp.cpu_count() works beautifully if we trust the rig.
    use_cores = min(args.cores, mp.cpu_count()) 
    
    if args.matrix:
        print(f"TELEMETRY: [ VERBOSE MATRIX WALL ENABLED ]")
    else:
        print(f"TELEMETRY: [ SILENT BENCHMARK MODE ]")
        
    print(f"ENGAGING {use_cores} LOGICAL THREADS...")
    print(f"Hunting for Absolute Zero Invariants...\n")
    
    workers = []
    try:
        for i in range(use_cores):
            p = mp.Process(target=hunt_curve_batch, args=(i, args.matrix))
            p.start()
            workers.append(p)
            
        for p in workers:
            p.join()
            
    except KeyboardInterrupt:
        print("\n[!] KeyboardInterrupt received. Safely collapsing Strix Matrix Array...")
        for p in workers:
            p.terminate()
        sys.exit(0)
