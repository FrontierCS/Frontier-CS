#include <iostream>
#include <vector>
#include <algorithm>
#include <cstdlib>

using namespace std;

// Global variables to maintain state
int N;
int current_r = 0;
int pairs_found = 0;
// matched[x] is true if slice x has been paired and reported
bool matched[86005];

// Query function: toggles slice x in the device
int ask(int x) {
    cout << "? " << x << endl;
    int r;
    cin >> r;
    current_r = r;
    return r;
}

// Report function: outputs a found pair
void report(int a, int b) {
    cout << "! " << a << " " << b << endl;
    matched[a] = true;
    matched[b] = true;
    pairs_found++;
    if (pairs_found == N) {
        exit(0);
    }
}

// Recursive solver
// Precondition: Elements in P and M are currently IN the device.
// Postcondition: Elements in P and M are OUT of the device.
void solve(const vector<int>& P, const vector<int>& M) {
    // If no matched elements to find, just clear P from device
    if (M.empty()) {
        for (int x : P) ask(x);
        return;
    }
    // Base case: 1 unmatched element implies the single element in M is its partner
    if (P.size() == 1) {
        report(P[0], M[0]);
        // Remove both from device
        ask(P[0]);
        ask(M[0]);
        return;
    }

    // Split P into two halves
    int mid = P.size() / 2;
    vector<int> P_L, P_R;
    P_L.reserve(mid);
    P_R.reserve(P.size() - mid);
    for (int i = 0; i < mid; ++i) P_L.push_back(P[i]);
    for (int i = mid; i < P.size(); ++i) P_R.push_back(P[i]);

    // Toggle P_L OUT. P_R remains IN.
    for (int x : P_L) ask(x);

    // Classify M into M_L (partners in P_L) and M_R (partners in P_R)
    vector<int> M_L, M_R;
    M_L.reserve(M.size());
    M_R.reserve(M.size());

    int prev = current_r;
    for (int u : M) {
        ask(u); // Toggle u OUT
        // If count decreased, u was contributing to distinct count.
        // Since P_R is IN and P_L is OUT, this means partner is NOT in P_R.
        // Thus partner is in P_L.
        if (current_r < prev) {
            M_L.push_back(u);
            // Leave u OUT
        } else {
            // Count stayed same (or increased, but logically same here since pair exists)
            // Partner is in P_R.
            M_R.push_back(u);
            // We need u IN for the recursive call on (P_R, M_R)
            ask(u); 
        }
        prev = current_r;
    }

    // Current State: P_L OUT, P_R IN. M_L OUT, M_R IN.
    
    // Solve for right half (starts IN, ends OUT)
    solve(P_R, M_R);
    
    // Current State: P_L OUT, P_R OUT, M_L OUT, M_R OUT.

    // Prepare for left half: Toggle P_L and M_L IN
    for (int x : P_L) ask(x);
    for (int x : M_L) ask(x);

    // Solve for left half (starts IN, ends OUT)
    solve(P_L, M_L);
    
    // Final State: All passed P and M are OUT.
}

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> N)) return 0;

    vector<int> P; // Unmatched items
    vector<int> M; // Matched items (partners are in P)
    P.reserve(2 * N);
    M.reserve(2 * N);

    for (int i = 1; i <= 2 * N; ++i) {
        int prev = current_r;
        ask(i);
        if (current_r == prev) {
            // Partner is already in the device (so in P)
            M.push_back(i);
        } else {
            // Partner is not in the device
            P.push_back(i);
        }

        // Trigger solver if we have accumulated enough matches or at the end
        // The ratio 0.6 balances the overhead of processing P vs accumulating M
        bool force = (i == 2 * N);
        if (!M.empty() && (force || M.size() >= P.size() * 0.6)) {
            solve(P, M);
            
            // solve() leaves all P and M OUT.
            // Elements in M are now paired with some in P and handled.
            // Elements in P that were NOT matched need to be put back IN.
            vector<int> next_P;
            next_P.reserve(P.size());
            for (int x : P) {
                if (!matched[x]) {
                    next_P.push_back(x);
                    ask(x); // Toggle IN
                }
            }
            P = next_P;
            M.clear();
        }
    }

    return 0;
}