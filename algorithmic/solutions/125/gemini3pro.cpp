#include <iostream>
#include <vector>
#include <algorithm>

using namespace std;

// Global variables to track state
int N;
int current_distinct = 0;
vector<bool> in_device;

// Perform a query on slice x
int query(int x) {
    cout << "? " << x << "\n";
    cout.flush();
    int r;
    cin >> r;
    // Update our internal tracking
    in_device[x] = !in_device[x];
    current_distinct = r;
    return r;
}

// Output the answer for a pair
void answer(int a, int b) {
    cout << "! " << a << " " << b << "\n";
    cout.flush();
}

/**
 * Solve function to match elements from Q to elements from M.
 * 
 * M: Subset of indices from the "first occurrences" set. All elements in M are currently in the same state (m_in).
 * Q: Subset of indices from the "second occurrences" set. Elements in Q match elements in M 1-to-1.
 * m_in: The current state (true=IN, false=OUT) of all elements in M.
 */
void solve_optimized(vector<int>& M, vector<int>& Q, bool m_in) {
    if (M.empty()) return;
    
    // Base case: if only 1 element in M, it must match the only element in Q.
    if (M.size() == 1) {
        answer(M[0], Q[0]);
        return;
    }

    // Split M into two halves
    int half = M.size() / 2;
    vector<int> M_L, M_R;
    M_L.reserve(half);
    M_R.reserve(M.size() - half);
    for (int i = 0; i < half; ++i) M_L.push_back(M[i]);
    for (int i = half; i < M.size(); ++i) M_R.push_back(M[i]);

    // Toggle M_L to the opposite state of m_in.
    // This allows us to distinguish between M_L and M_R by observing count changes.
    for (int x : M_L) {
        query(x);
    }
    bool m_L_in = !m_in;
    // M_R remains in state m_in

    // We will classify Q into Q_L (matches M_L) and Q_R (matches M_R).
    vector<int> Q_L, Q_R;
    Q_L.reserve(M_L.size());
    Q_R.reserve(M_R.size());
    int target_L = M_L.size();
    int target_R = M_R.size();
    
    for (int q : Q) {
        // Optimization: if one bin is full, the remaining items must go to the other.
        // This saves queries, crucial for N=43000.
        if (Q_L.size() == target_L) {
            Q_R.push_back(q);
            continue;
        }
        if (Q_R.size() == target_R) {
            Q_L.push_back(q);
            continue;
        }

        // We need to query q to check its partner.
        // We toggle q and check the change in distinct count.
        bool was_in = in_device[q];
        int r_prev = current_distinct;
        int r_curr = query(q); // Toggle q
        int delta = r_curr - r_prev;
        
        bool partner_is_in;
        // Logic to determine if partner is currently IN based on toggle result
        if (!was_in) { // Moved OUT -> IN
            // If partner is IN, count doesn't change (delta 0).
            // If partner is OUT, count increases (delta +1).
            partner_is_in = (delta == 0);
        } else { // Moved IN -> OUT
            // If partner is IN, count doesn't change (delta 0).
            // If partner is OUT, count decreases (delta -1).
            partner_is_in = (delta == 0);
        }
        
        // If partner's state matches M_L's state, it belongs to Left.
        if (partner_is_in == m_L_in) {
            Q_L.push_back(q);
        } else {
            Q_R.push_back(q);
        }
    }
    
    // Recursive calls
    solve_optimized(M_L, Q_L, m_L_in);
    solve_optimized(M_R, Q_R, m_in);
}

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> N)) return 0;
    
    in_device.assign(2 * N + 1, false);
    
    vector<int> M, Q;
    M.reserve(N);
    Q.reserve(N);

    // Initial pass: categorize into First Occurrences (M) and Second Occurrences (Q)
    // We leave all items IN the device to start in a known state (State 1: All IN).
    for (int i = 1; i <= 2 * N; ++i) {
        int prev = current_distinct;
        query(i);
        if (current_distinct > prev) {
            // Count increased -> new kind
            M.push_back(i);
        } else {
            // Count same -> partner already in M
            Q.push_back(i);
        }
    }
    
    // Solve the matching problem
    // Initially, all elements of M are IN (m_in = true).
    solve_optimized(M, Q, true);
    
    return 0;
}