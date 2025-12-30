#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <iomanip>

using namespace std;

// Constants
// X_VAL must be large enough to separate the lines according to their slopes.
// The separation between lines with slopes a and a+1 is approximately X_VAL.
// We need this separation to be larger than the range of b, which is [-10000, 10000].
// 6e7 is sufficient (> 20000).
const double X_VAL = 6e7; 

// Globals
int N;
vector<int> found_a;
double total_w_sum = 0.0;

// Helper to calculate weight w_i = 1 / sqrt(a_i^2 + 1)
double get_w(int a) {
    return 1.0 / sqrt(1.0 + (double)a * a);
}

// Query function
double query(double x, double y) {
    cout << "? " << fixed << setprecision(10) << x << " " << y << endl;
    double ret;
    cin >> ret;
    return ret;
}

// H function: query at (X_VAL, u * X_VAL)
// Effectively queries the function H(u) related to f(X, uX).
double query_H(double u) {
    return query(X_VAL, u * X_VAL);
}

// Recursive function to find slopes a_i in range [L, R]
// hL = H(L), hR = H(R), S_left is the slope of H at L (from the left side recursion)
void find_slopes(double L, double R, double hL, double hR, double S_left) {
    // Calculate the slope of the secant line
    double calc_slope = (hR - hL) / (R - L);
    
    // If the secant slope matches the expected slope from the left, 
    // it implies there are no "kinks" (lines) in this interval.
    // We use a small tolerance for floating point comparisons.
    if (abs(calc_slope - S_left) < 1e-9) {
        return;
    }

    // Try to fit a single line 'a' inside (L, R)
    // If there is exactly one line at integer 'a' in this range, then:
    // H(R) - H(L) = S_left * (a - L) + (S_left + 2*w(a)) * (R - a)
    // Rearranging for the term depending on 'a':
    // 2 * w(a) * (R - a) = (hR - hL) - S_left * (R - L)
    double val = (hR - hL) - S_left * (R - L);
    
    int best_a = -20000;
    double best_err = 1e18;
    
    int start_k = floor(L) + 1;
    int end_k = ceil(R) - 1;
    
    // Search for the best integer 'a' that fits the single line hypothesis
    if (start_k <= end_k) {
        for (int k = start_k; k <= end_k; ++k) {
            double target = 2.0 * get_w(k) * (R - k);
            double err = abs(val - target);
            if (err < best_err) {
                best_err = err;
                best_a = k;
            }
        }
    }

    // If we found a candidate, we verify it by querying a midpoint.
    // This allows us to confirm the single line or split if needed.
    // This consumes 1 query but potentially saves recursion.
    if (best_a != -20000) {
        // Choose midpoint carefully to be a half-integer
        double Mid = floor((L + R) / 2.0) + 0.5;
        // Avoid boundary issues
        if (Mid <= L + 0.1 || Mid >= R - 0.1) Mid = L + 0.5;
        if (Mid >= R - 0.1) Mid = L + (R-L)/2.0; 

        double hMid = query_H(Mid);
        
        // Predict H(Mid) assuming only 'best_a' is present in (L, R)
        double pred_hMid;
        if (Mid < best_a) {
             pred_hMid = hL + S_left * (Mid - L);
        } else {
             pred_hMid = hL + S_left * (best_a - L) + (S_left + 2.0 * get_w(best_a)) * (Mid - best_a);
        }
        
        // Check if prediction matches observed value
        // The absolute values are large (~1e14), so tolerance must be appropriate.
        // However, within the local structure, precision is usually good.
        if (abs(hMid - pred_hMid) < 1.0) { 
            found_a.push_back(best_a);
            return;
        }
        
        // If verification fails, it means there are multiple lines (or the fit was wrong).
        // We recurse using the obtained midpoint value.
        find_slopes(L, Mid, hL, hMid, S_left);
        
        // Calculate S_mid for the right interval
        double S_mid = S_left;
        for (int a : found_a) {
            if (a > L && a < Mid) {
                S_mid += 2.0 * get_w(a);
            }
        }
        find_slopes(Mid, R, hMid, hR, S_mid);
        return;
    }
    
    // Fallback split if no candidate found (unlikely given logic, but safe)
    double Mid = floor((L + R) / 2.0) + 0.5;
    double hMid = query_H(Mid);
    find_slopes(L, Mid, hL, hMid, S_left);
    double S_mid = S_left;
    for (int a : found_a) {
        if (a > L && a < Mid) {
            S_mid += 2.0 * get_w(a);
        }
    }
    find_slopes(Mid, R, hMid, hR, S_mid);
}

int main() {
    cin >> N;
    
    // 1. Determine total weight sum using two queries at x=0
    // At large Y, f(0, Y) is linear with slope sum(w_i).
    double Y_large = 1e11;
    double val_pos = query(0, Y_large);
    double val_neg = query(0, -Y_large);
    total_w_sum = (val_pos + val_neg) / (2.0 * Y_large);
    
    // The slope of H(u) starts at -sum(w_i) for very small u
    double S_start = -total_w_sum;
    
    // 2. Find all slopes a_i
    double L = -10000.5;
    double R = 10000.5;
    double hL = query_H(L);
    double hR = query_H(R);
    
    find_slopes(L, R, hL, hR, S_start);
    
    sort(found_a.begin(), found_a.end());
    
    // 3. Find b_i for each identified a_i
    vector<int> found_b;
    double current_slope = -total_w_sum;
    
    for (int i = 0; i < found_a.size(); ++i) {
        int a = found_a[i];
        double w = get_w(a);
        
        // M1: slope to the left of the kink at X_VAL
        // M2: slope to the right of the kink
        double M1 = current_slope;
        double M2 = current_slope + 2.0 * w;
        
        // The kink for line i at x=X_VAL is at y = a*X_VAL + b_i.
        // We query two points bracketing the possible location of the kink.
        double y_center = a * X_VAL;
        double y_down = y_center - 20000.0;
        double y_up = y_center + 20000.0;
        
        double f_down = query(X_VAL, y_down);
        double f_up = query(X_VAL, y_up);
        
        // Using the change in function value and known slopes to find intersection
        // Y_kink * (M2 - M1) = f_down - f_up - M1*y_down + M2*y_up
        double rhs = (f_down - f_up) - M1 * y_down + M2 * y_up;
        double Y_kink = rhs / (2.0 * w);
        
        double b_val = Y_kink - y_center;
        int b_int = round(b_val);
        found_b.push_back(b_int);
        
        current_slope += 2.0 * w;
    }
    
    cout << "!";
    for (int x : found_a) cout << " " << x;
    for (int x : found_b) cout << " " << x;
    cout << endl;
    
    return 0;
}