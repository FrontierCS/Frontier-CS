#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <iomanip>

using namespace std;

// Use long double for high precision coordinates and values
typedef long double ld;

// Constants
// X coordinate for the vertical line scan. 10^10 ensures lines are sorted by slope.
const ld XR = 1e10; 
// Y range at XR covers all possible line intersections.
const ld Y_MIN = -2e14 - 5e10; 
const ld Y_MAX = 2e14 + 5e10;

// Epsilon for consistency checks.
// Values are around 10^16, so 1.0 is a very tight relative tolerance but loose enough for float noise.
const ld EPS = 100.0; 

// Delta for slope measurement.
// Needs to be large enough to overcome precision loss (g ~ 10^16)
// but small enough to likely stay within a linear segment (gap ~ 10^10).
const ld DELTA = 1e7;

int N;

// Query the interactor
ld query(ld x, ld y) {
    cout << "? " << fixed << setprecision(10) << x << " " << y << endl;
    ld res;
    cin >> res;
    return res;
}

struct Kink {
    ld y;
    ld slope_change;
};

vector<Kink> kinks;

// Compute slope at x, y using a secant approximation
ld get_slope(ld x, ld y) {
    ld v1 = query(x, y);
    ld v2 = query(x, y + DELTA);
    return (v2 - v1) / DELTA;
}

// Recursive function to find all kinks in [L, R]
// gL = g(L), sL = slope on segment starting at L (towards R)
// gR = g(R), sR = slope on segment ending at R (from L)
void solve(ld x, ld L, ld gL, ld sL, ld R, ld gR, ld sR) {
    // Estimate kink position by intersecting tangents
    if (abs(sL - sR) < 1e-12) return; 
    
    ld M = (gR - gL + sL * L - sR * R) / (sL - sR);
    
    // Clamp M to be strictly inside (L, R)
    if (M < L + 1.0) M = L + 1.0;
    if (M > R - 1.0) M = R - 1.0;
    
    ld gM = query(x, M);
    
    // Check if M lies on the left tangent
    ld expected_L = gL + sL * (M - L);
    bool left_linear = abs(gM - expected_L) < EPS;
    
    // Check if M lies on the right tangent
    ld expected_R = gR + sR * (M - R);
    bool right_linear = abs(gM - expected_R) < EPS;
    
    if (left_linear && right_linear) {
        // M is the unique kink in this interval
        // sR - sL is the change in slope at this kink
        kinks.push_back({M, sR - sL});
        return;
    }
    
    if (left_linear) {
        // No kinks in (L, M). M is just a point on the line from L.
        // The slope to the left of the kink-containing subinterval (M, R) is sL.
        solve(x, M, gM, sL, R, gR, sR);
        return;
    }
    
    if (right_linear) {
        // No kinks in (M, R).
        // Recurse on (L, M).
        solve(x, L, gL, sL, M, gM, sR);
        return;
    }
    
    // Kinks exist in both (L, M) and (M, R).
    // Measure slope at M to split the problem.
    ld sM = get_slope(x, M);
    
    solve(x, L, gL, sL, M, gM, sM);
    solve(x, M, gM, sM, R, gR, sR);
}

int main() {
    // Optimize I/O
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> N;
    
    ld x = XR;
    
    // Initial boundaries
    ld L = Y_MIN;
    ld R = Y_MAX;
    
    ld gL = query(x, L);
    ld sL = get_slope(x, L);
    
    ld gR = query(x, R);
    // Slope at R needs to be the slope to the left of R. 
    // get_slope measures forward difference, so use R - DELTA.
    ld v_prev = query(x, R - DELTA);
    ld sR = (gR - v_prev) / DELTA;
    
    solve(x, L, gL, sL, R, gR, sR);
    
    // Sort kinks by Y coordinate
    sort(kinks.begin(), kinks.end(), [](const Kink& a, const Kink& b) {
        return a.y < b.y;
    });
    
    vector<long long> a_res;
    vector<long long> b_res;
    
    // Reconstruct lines
    // At x = 10^10, the lines are sorted by slope a_i.
    // kinks[i] corresponds to the line with the i-th smallest a_i.
    for (int i = 0; i < N; ++i) {
        // Estimate magnitude of a from slope change
        // change = 2 / sqrt(a^2 + 1)
        // a = sqrt( 4/change^2 - 1 )
        ld sc = kinks[i].slope_change;
        ld val = 4.0 / (sc * sc) - 1.0;
        if (val < 0) val = 0;
        long long a_est = round(sqrt(val));
        
        bool found = false;
        // Search neighborhood for the integer a that yields an integer b in range
        for (long long a_cand = a_est - 50; a_cand <= a_est + 50; ++a_cand) {
            // Check positive candidate
            if (a_cand >= -10000 && a_cand <= 10000) {
                ld b_val = kinks[i].y - a_cand * x;
                long long b_round = round(b_val);
                if (abs(b_round) <= 10000 && abs(b_val - b_round) < 1.0) { // Check residual and range
                    a_res.push_back(a_cand);
                    b_res.push_back(b_round);
                    found = true;
                    break;
                }
            }
            // Check negative candidate
            long long a_neg = -a_cand;
            if (a_neg >= -10000 && a_neg <= 10000) {
                ld b_val = kinks[i].y - a_neg * x;
                long long b_round = round(b_val);
                if (abs(b_round) <= 10000 && abs(b_val - b_round) < 1.0) {
                    a_res.push_back(a_neg);
                    b_res.push_back(b_round);
                    found = true;
                    break;
                }
            }
        }
        
        // Fallback (should not be reached)
        if (!found) {
            a_res.push_back(a_est);
            b_res.push_back(0);
        }
    }

    cout << "!";
    for (auto val : a_res) cout << " " << val;
    for (auto val : b_res) cout << " " << val;
    cout << endl;

    return 0;
}