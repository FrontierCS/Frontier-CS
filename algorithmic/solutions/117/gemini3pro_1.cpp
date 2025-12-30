#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <map>
#include <iomanip>

using namespace std;

typedef long long ll;
typedef long double ld;

const ll X = 1e8;
const int MIN_SLOPE = -10000;
const int MAX_SLOPE = 10000;
const ld EPS = 1.0; // Threshold for linearity check. Given large X, deviations are large.

map<int, ld> cache;

// Query function with memoization
ld query(int k) {
    if (cache.count(k)) return cache[k];
    // k corresponds to y = (k + 0.5) * X
    // This point is roughly halfway between the "kink" for slope k and slope k+1
    ld y = (ld)(k) + 0.5;
    y *= X;
    cout << "? " << X << " " << fixed << setprecision(10) << y << endl;
    ld ret;
    cin >> ret;
    return cache[k] = ret;
}

vector<int> found_slopes;

// Recursive Divide & Conquer to find active slopes
void solve(int L, int R) {
    // We are looking for slopes in the range (L, R], i.e., integers L+1, ..., R.
    // We have queries at L and R (indices correspond to boundaries).
    
    if (L >= R) return;
    
    // Linearity check logic:
    // If the function S(X, y) is linear on the interval [y_L, y_R], then there are no lines with slopes in (L, R].
    // We check the midpoint.
    
    int mid = (L + R) / 2;
    
    // If L+1 == R, we are at an atomic interval containing slope R.
    // The caller must have verified that (L, R] is non-linear (or part of a non-linear larger interval).
    // However, the caller only checked that (ParentL, ParentR) is non-linear.
    // We need to be careful.
    
    // Actually, simply checking linearity on [L, R] is sufficient.
    // We need Q(L), Q(R) and Q(mid).
    // If they are collinear, then likely no lines in (L, R].
    
    // Special base case for recursion
    if (L + 1 == R) {
        // If we reached here, it implies the range (L, R] is suspected to contain a line.
        // But since we pruned linear ranges, we assume it does.
        // Wait, if solve(L, R) is called, it means the parent range was non-linear.
        // But the non-linearity could be in the sibling half.
        // We must check linearity before recursing, or check here?
        // We cannot check linearity of (L, L+1) because there is no midpoint integer.
        // But we rely on the fact that if (L, R) was linear we wouldn't be here.
        // So if we are here and L+1==R, slope R is active.
        found_slopes.push_back(R);
        return;
    }

    ld qL = query(L);
    ld qR = query(R);
    ld qMid = query(mid);
    
    // Check if qMid lies on the line connecting qL and qR
    // The x-coordinates (in terms of index) are L, mid, R.
    // Expected qMid if linear:
    ld expected = qL + (qR - qL) * (ld)(mid - L) / (ld)(R - L);
    
    if (abs(qMid - expected) < EPS) {
        // Linear, so no lines in (L, R].
        return;
    }
    
    // Non-linear, so there are lines. Recurse.
    solve(L, mid);
    solve(mid, R);
}

int main() {
    // Optimize I/O
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    if (!(cin >> n)) return 0;

    // Range of possible slopes
    int L = MIN_SLOPE - 1;
    int R = MAX_SLOPE;
    
    // Ensure endpoints are cached
    query(L);
    query(R);
    
    // Start D&C
    // Initial linearity check is not needed as we know there are lines, 
    // but the function handles it.
    // Actually, solve(L, R) checks linearity of L..R first.
    // However, if the entire range is linear (impossible for N>=1), it would return.
    // But solve implementation above checks linearity of L..R using `mid`.
    // It works.
    
    solve(L, R);
    
    vector<int> a = found_slopes;
    sort(a.begin(), a.end());
    
    // Calculate b for each a
    vector<int> b(a.size());
    
    // Precompute total C
    ld C_total = 0;
    vector<ld> c_vals(a.size());
    for(int i=0; i<(int)a.size(); ++i) {
        c_vals[i] = 1.0 / sqrt(pow((ld)a[i], 2) + 1.0);
        C_total += c_vals[i];
    }
    
    // D depends on the position in the sorted list of slopes
    ld current_sum = 0;
    for(int i=0; i<(int)a.size(); ++i) {
        ld ci = c_vals[i];
        // D is sum(c_j for j < i) - sum(c_j for j > i)
        // sum(c_j for j > i) = C_total - current_sum - ci
        // D = current_sum - (C_total - current_sum - ci) = 2*current_sum + ci - C_total
        ld D = 2 * current_sum + ci - C_total;
        current_sum += ci;
        
        // We need Q_L and Q_R surrounding the kink for a[i]
        // Kink is at approx a[i]*X.
        // Surrounding queries are at indices a[i]-1 and a[i].
        // Corresponding y values: Y_L = (a[i]-0.5)X, Y_R = (a[i]+0.5)X
        
        ld q_l = query(a[i]-1);
        ld q_r = query(a[i]);
        
        // Derived formula for K = a[i]*X + b[i]
        // K = (Q_L - Q_R + D*X + 2*ci*a[i]*X) / (2*ci)
        
        ld num = q_l - q_r + D * X + 2 * ci * a[i] * X;
        ld K = num / (2 * ci);
        
        ld val_b = K - (ld)a[i] * X;
        b[i] = (int)round(val_b);
    }
    
    cout << "!";
    for(int x : a) cout << " " << x;
    for(int x : b) cout << " " << x;
    cout << endl;
    
    return 0;
}