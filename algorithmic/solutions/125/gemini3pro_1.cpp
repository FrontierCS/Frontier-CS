#include <iostream>
#include <vector>
#include <algorithm>
#include <numeric>

using namespace std;

// Global to keep track of current device state response
int current_distinct_count = 0;

// Function to toggle a slice
// Returns the new number of distinct kinds
int query(int x) {
    cout << "? " << x << endl;
    int r;
    cin >> r;
    return r;
}

// Function to report a pair
void answer(int a, int b) {
    cout << "! " << a << " " << b << endl;
}

// Helper to move items from one state to another (loaded/unloaded)
// Only needed if we want to explicitly manage state, but we integrate it.

// Recursive solver
// U: set of minerals to pair (either internally or with E)
// E: set of external minerals known to pair with some subset of U
// U_loaded: boolean indicating if all elements of U are currently IN the device.
//           Elements of E are assumed OUT of the device initially.
void solve(vector<int>& U, vector<int>& E, bool U_loaded) {
    if (U.empty()) return;

    // Base case: If U has 1 element, E must have 1 element, they are a pair.
    if (U.size() == 1) {
        answer(U[0], E[0]);
        // Clean up: U[0] is in device if U_loaded is true. E[0] is out.
        // We need to leave the device in the state expected by the caller.
        // The contract is: "cleans up U and E from device".
        // If U_loaded is true, U[0] is IN. We should remove it.
        if (U_loaded) {
            query(U[0]);
        }
        // E[0] is OUT, so nothing to do.
        return;
    }

    int mid = U.size() / 2;
    vector<int> L(U.begin(), U.begin() + mid);
    vector<int> R(U.begin() + mid, U.end());

    // Manage device state to have exactly L loaded
    if (U_loaded) {
        // U is loaded (L and R are IN). We need only L.
        // Unload R.
        for (int x : R) {
            query(x);
        }
    } else {
        // Nothing loaded. Load L.
        for (int x : L) {
            query(x);
        }
    }
    // Now distinct count reflects L being in device.
    int baseline = current_distinct_count; // Actually we don't track this locally, we rely on delta.

    vector<int> E_L, E_R;
    // Classify E
    // Elements of E are currently OUT.
    int prev_r = -1; // We can track r if needed, but we just check change.
    // However, since we might do multiple queries, we need to know the 'current' r.
    // We can maintain a global tracker or just read from cin.
    // Let's assume the query function handles IO.
    // To detect change, we need to know r before toggle.
    // But we don't store r globally in a synchronized way easily without extra query? 
    // Wait, query returns r.
    // We need r BEFORE query.
    // We can track r manually? No, simpler to just assume proper state.
    // We need to know if r increased or stayed same.
    // BUT we don't know the current r before the first toggle of the loop.
    // Solution: use the return value of the previous operation.
    // But for the very first operation?
    // We can do a dummy query? No.
    // Better: We track the expected r? No.
    // The problem is we toggle x. If r_new == r_old, match L.
    // We need r_old.
    // Optimization: The very first time we load L, we get the count.
    // When we unload R, we get the count.
    // So we can pass 'current_r' around.
    
    // Let's refactor to track current r globally?
    // No, local tracking is safer.
    // Let's re-do the load/unload with tracking.
    
    // We need to re-implement query to update a tracker?
    // No, just use a variable.
}

// Improved solver with current_r tracking
void solve_recursive(vector<int>& U, vector<int>& E, bool U_loaded, int& current_r) {
    if (U.empty()) return;

    if (U.size() == 1) {
        answer(U[0], E[0]);
        if (U_loaded) {
            current_r = query(U[0]); // Unload U[0]
        }
        return;
    }

    int mid = U.size() / 2;
    vector<int> L(U.begin(), U.begin() + mid);
    vector<int> R(U.begin() + mid, U.end());

    // Adjust device to have L loaded, R unloaded
    if (U_loaded) {
        // U is loaded (L+R). Unload R.
        for (int x : R) {
            current_r = query(x);
        }
    } else {
        // Nothing loaded. Load L.
        for (int x : L) {
            current_r = query(x);
        }
    }

    vector<int> E_L, E_R;
    // Classify E
    for (int x : E) {
        int next_r = query(x); // Toggle IN
        if (next_r == current_r) {
            // Match found in L (count didn't increase)
            // Leave x IN
            E_L.push_back(x);
        } else {
            // No match in L (count increased)
            E_R.push_back(x);
            // Toggle OUT
            next_r = query(x);
        }
        current_r = next_r;
    }

    vector<int> R_ext, R_int;
    // Classify R
    for (int x : R) {
        int next_r = query(x); // Toggle IN
        if (next_r == current_r) {
            // Match found in L
            // Leave x IN
            R_ext.push_back(x);
        } else {
            // No match in L (match in R or internal R pair)
            // But since R is unloaded, this means it's a new type or match with something else?
            // R items are candidates to pair with L or pair internally.
            // If match L, count same.
            // If match internal R? Since other R are OUT, it introduces new type.
            // So count increases.
            R_int.push_back(x);
            // Toggle OUT
            next_r = query(x);
        }
        current_r = next_r;
    }

    // Now device contains L + E_L + R_ext.
    // These are exactly the items needed for the first recursive call (as "loaded").
    // E_L and R_ext serve as the external partners for L.
    vector<int> next_E_L = E_L;
    next_E_L.insert(next_E_L.end(), R_ext.begin(), R_ext.end());
    
    solve_recursive(L, next_E_L, true, current_r);
    
    // After return, L and its partners are removed from device.
    // Device should be empty (relative to these items).
    // Now solve for R_int and E_R.
    // They are currently OUT.
    solve_recursive(R_int, E_R, false, current_r);
}

int main() {
    int N;
    if (!(cin >> N)) return 0;

    vector<int> U(2 * N);
    iota(U.begin(), U.end(), 1);
    
    // Shuffle for random average case
    // Using a simple fixed seed or just rand() is fine
    srand(12345);
    random_shuffle(U.begin(), U.end());

    vector<int> E;
    int current_r = 0;
    
    solve_recursive(U, E, false, current_r);

    return 0;
}