#include <iostream>
#include <vector>
#include <cmath>
#include <iomanip>
#include <algorithm>
#include <map>

using namespace std;

typedef long long ll;
typedef long double ld;

// Choose X small enough to minimize precision errors but large enough to separate windows.
// Window for a=k is [k*X - 10000, k*X + 10000].
// Need (k+1)*X - 10000 > k*X + 10000 => X > 20000.
// X = 20005 is safe.
const ll X_CONST = 20005;
const ll OFFSET = -12000; // y = k*X + OFFSET. Shift to be between windows.

int N;
map<ll, ld> cache;

ld query_idx(ll k) {
    if (cache.count(k)) return cache[k];
    ld x = (ld)X_CONST;
    ld y = (ld)k * X_CONST + OFFSET;
    cout << "? " << fixed << setprecision(0) << x << " " << fixed << setprecision(5) << y << endl;
    ld ans;
    cin >> ans;
    return cache[k] = ans;
}

struct Line {
    int a, b;
};

vector<Line> found_lines;

void solve(int L, int R, ld vL, ld vR) {
    ld yL = (ld)L * X_CONST + OFFSET;
    ld yR = (ld)R * X_CONST + OFFSET;
    ld yM, vM;
    ld h1, h2;
    int M = 0;
    
    if (L + 1 == R) {
        yM = (yL + yR) / 2.0;
        cout << "? " << fixed << setprecision(0) << (ld)X_CONST << " " << fixed << setprecision(5) << yM << endl;
        cin >> vM;
        h1 = yM - yL;
        h2 = yR - yM;
    } else {
        M = (L + R) / 2;
        yM = (ld)M * X_CONST + OFFSET;
        vM = query_idx(M);
        h1 = yM - yL;
        h2 = yR - yM;
    }
    
    // Linearity check
    ld s1 = (vM - vL) / h1;
    ld s2 = (vR - vM) / h2;
    
    // If linear, interval is empty
    // Tolerance depends on precision. 
    if (abs(s1 - s2) < 1e-4) {
        return; 
    }
    
    int candidate_cnt = 0;
    Line best_cand = {0, 0};
    
    // Try to fit 1 line
    // Iterate a in [L, R-1]
    for (int a = L; a < R; ++a) {
        ld w = 1.0 / sqrt((ld)a * a + 1.0);
        ld two_w = 2.0 * w;
        
        // Calculate y_star assuming case 1 (y* <= yM)
        // From derivation: 2 w y* = term2 * h1 - (vM - vL - w(yM + yL))
        // term2 = (vR - vM - w * (yR - yM)) / h2
        ld term2 = (vR - vM - w * (yR - yM)) / h2;
        ld rhs1 = term2 * h1 - (vM - vL - w * (yM + yL));
        ld y_star1 = rhs1 / two_w;
        
        bool ok1 = (y_star1 > yL - 1e-3 && y_star1 <= yM + 1e-3);
        
        // Case 2 (y* > yM)
        // 2 w y* = term1 * h2 - (vR - vM - w * (yR + yM))
        // term1 = (vM - vL - w * (yM - yL)) / h1
        ld term1 = (vM - vL - w * (yM - yL)) / h1;
        ld rhs2 = term1 * h2 - (vR - vM - w * (yR + yM));
        ld y_star2 = rhs2 / two_w;
        
        bool ok2 = (y_star2 > yM - 1e-3 && y_star2 < yR + 1e-3);
        
        ld y_final = -1e18;
        if (ok1 && !ok2) y_final = y_star1;
        else if (!ok1 && ok2) y_final = y_star2;
        else if (ok1 && ok2) {
            if (abs(y_star1 - y_star2) < 1e-3) y_final = y_star1;
            else y_final = y_star1; // Prefer one
        }
        
        if (y_final > -1e17) {
            ld b_ld = y_final - (ld)a * X_CONST;
            long long b_round = round(b_ld);
            // Check consistency and range
            if (abs(b_ld - b_round) < 0.2 && b_round >= -10000 && b_round <= 10000) {
                candidate_cnt++;
                best_cand = {a, (int)b_round};
            }
        }
    }
    
    if (candidate_cnt == 1) {
        found_lines.push_back(best_cand);
        return;
    }
    
    // If ambiguous or 0 candidates (due to noise or multiple lines), split
    if (L + 1 < R) {
        solve(L, M, vL, vM);
        solve(M, R, vM, vR);
    }
}

int main() {
    // Fast IO not strictly needed for interactive, but good practice
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    if (!(cin >> N)) return 0;
    
    int L = -10000;
    int R = 10001; 
    
    // Pre-query boundaries
    query_idx(L);
    query_idx(R);
    
    solve(L, R, cache[L], cache[R]);
    
    cout << "!";
    for (auto &l : found_lines) cout << " " << l.a;
    for (auto &l : found_lines) cout << " " << l.b;
    cout << endl;
    
    return 0;
}