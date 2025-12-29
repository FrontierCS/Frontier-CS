#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <iomanip>

using namespace std;

// Use long double for better precision with large coordinates and small weights
typedef long double ld;

int N;
// X coordinate chosen to be large enough to separate all lines
// max|b| = 10000. separation > 2*10000. X=40000 is good.
const ld X = 40000.0;
// Range of Y to search. max|a|*X + max|b| ~= 10000*40000 + 10000 = 400,010,000.
// Use a bit larger range to be safe.
const ld INF_Y = 600000000.0; 

// Function to query the interactor
ld query(ld x, ld y) {
    cout << "? " << fixed << setprecision(12) << x << " " << y << endl;
    ld res;
    cin >> res;
    return res;
}

vector<ld> corners;

// Recursive function to find corners
// L, R: current interval
// fL, sL: function value and slope at L (specifically, slope on [L, L+epsilon])
// fR, sR: function value and slope at R (specifically, slope on [R-epsilon, R])
void solve(ld L, ld R, ld fL, ld sL, ld fR, ld sR) {
    // If slope difference is negligible, there are no corners in this interval
    if (abs(sR - sL) < 1e-9) return;
    
    // Calculate intersection of tangent from left and tangent from right
    // M = (fL - fR + sR*R - sL*L) / (sR - sL)
    ld M = (fL - fR + sR * R - sL * L) / (sR - sL);
    
    // Clamp M to ensure it is strictly inside (L, R) to guarantee progress
    ld margin = 1e-2;
    if (M < L + margin) M = L + margin;
    if (M > R - margin) M = R - margin;
    
    // We query around M to get value and slopes
    // delta should be small enough not to cross multiple corners (separation > 20000)
    // but large enough for stable slope calculation. 1.0 is fine.
    ld delta = 0.5; 
    ld fM = query(X, M);
    ld fM_minus = query(X, M - delta);
    ld fM_plus = query(X, M + delta);
    
    ld sM_left = (fM - fM_minus) / delta;
    ld sM_right = (fM_plus - fM) / delta;
    
    // Check if M is close to a corner (significant change in slope at M)
    // If M lands exactly on a corner (or within delta), slopes will differ.
    // If M lands between corners, slopes should be roughly equal (linear segment).
    if (sM_right - sM_left > 1e-9) {
        corners.push_back(M);
    }
    
    // Recurse left if there is still slope change unaccounted for
    if (sM_left - sL > 1e-9) {
        solve(L, M, fL, sL, fM, sM_left);
    }
    // Recurse right
    if (sR - sM_right > 1e-9) {
        solve(M, R, fM, sM_right, fR, sR);
    }
}

struct Line {
    int a, b;
};

int main() {
    // Fast IO not needed for interactive, but good practice
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> N)) return 0;
    
    ld L = -INF_Y;
    ld R = INF_Y;
    
    // Initial queries at boundaries
    // We need slope entering the range and leaving the range
    // Since L is very small, slope at L is constant for y < L_corner_min
    ld fL = query(X, L);
    ld fL_plus = query(X, L + 1.0);
    ld sL = fL_plus - fL;
    
    ld fR = query(X, R);
    ld fR_minus = query(X, R - 1.0);
    ld sR = fR - fR_minus; // Slope is (f(R) - f(R-1))/1
    
    solve(L, R, fL, sL, fR, sR);
    
    vector<Line> ans;
    for (ld y : corners) {
        // y ~= a*X + b
        // a = round(y / X)
        long long a = round(y / X);
        long long b = round(y - a * X);
        ans.push_back({(int)a, (int)b});
    }
    
    // Output format: ! a1 a2 ... an b1 b2 ... bn
    cout << "!";
    for (auto& l : ans) cout << " " << l.a;
    for (auto& l : ans) cout << " " << l.b;
    cout << endl;
    
    return 0;
}