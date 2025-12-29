#include <iostream>
#include <vector>
#include <numeric>
#include <cmath>
#include <cstdlib>
#include <ctime>
#include <algorithm>

using namespace std;

// Interaction helper function to perform a query
int query(const vector<int>& q) {
    cout << "0";
    for (int x : q) {
        cout << " " << x;
    }
    cout << endl;
    int res;
    cin >> res;
    return res;
}

// Function to output the final guess
void guess(const vector<int>& p) {
    cout << "1";
    for (int x : p) {
        cout << " " << x;
    }
    cout << endl;
    exit(0);
}

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    srand(time(NULL));

    int n;
    if (!(cin >> n)) return 0;

    // p_ans[i] stores the value at position i (1-based index)
    vector<int> p_ans(n + 1, 0); 
    vector<int> unknown(n);
    iota(unknown.begin(), unknown.end(), 1); // Fill with 1, 2, ..., n

    // --- Phase 1: Find position of the value 1 ---
    // We use a binary search-like approach on the indices.
    // To distinguish if pos(1) is in set L or R, we use random fillers.
    {
        vector<int> current_u = unknown;
        while (current_u.size() > 1) {
            int sz = current_u.size();
            int mid = sz / 2;
            vector<int> L, R;
            for (int i = 0; i < mid; ++i) L.push_back(current_u[i]);
            for (int i = mid; i < sz; ++i) R.push_back(current_u[i]);

            // Map for fast checking if an index is in L
            vector<bool> in_L(n + 1, false);
            for (int x : L) in_L[x] = true;

            bool found_in_L = false;
            bool determined = false;
            
            // Probability that a random value v (from 2..n) lands in L is p = |L|/n.
            // If pos(1) is in L, we get an ambiguous Score 1 only if pos(v) is also in L.
            // The probability of this happening consistently is p^limit.
            // We set limit such that p^limit is very small (e.g., < 1e-9).
            double p = (double)L.size() / n;
            int limit = 30; // Default safe limit
            if (p < 0.5) {
                if (p > 1e-9) {
                    double val = -20.7 / log(p); // -20.7 approx ln(1e-9)
                    limit = (int)ceil(val);
                    if (limit < 2) limit = 2;
                    if (limit > 35) limit = 35;
                } else {
                    limit = 2;
                }
            }

            int tries = 0;
            while (tries < limit) {
                tries++;
                // Pick random v in [2, n]
                int v = 2 + rand() % (n - 1);
                
                vector<int> q(n);
                for (int i = 1; i <= n; ++i) {
                    if (in_L[i]) q[i-1] = 1;
                    else q[i-1] = v;
                }
                
                int score = query(q);
                // Score 2: pos(1) in L and pos(v) in L^c -> Definite L
                // Score 0: pos(1) in L^c and pos(v) in L -> Definite R
                // Score 1: Ambiguous (Both in L or Both in L^c)
                if (score == 2) {
                    found_in_L = true;
                    determined = true;
                    break;
                } else if (score == 0) {
                    found_in_L = false;
                    determined = true;
                    break;
                }
            }
            
            if (!determined) {
                // If we consistently get Score 1, it implies we are in the "common" ambiguous case.
                // If pos(1) were in L (size |L|), ambiguity requires pos(v) in L. This is rare if |L| is small.
                // If pos(1) were in R, ambiguity requires pos(v) in L^c. This is common if |L| is small.
                // Therefore, timeout implies pos(1) is in R.
                found_in_L = false;
            }

            if (found_in_L) current_u = L;
            else current_u = R;
        }
        p_ans[current_u[0]] = 1;
    }

    // --- Phase 2: Find positions of 2, 3, ..., n ---
    // Since we know pos(1), we can use the value 1 as a "non-matching" filler for unknown positions
    // because P[unknown] != 1.
    vector<bool> position_filled(n + 1, false);
    for(int i=1; i<=n; ++i) if(p_ans[i] != 0) position_filled[i] = true;

    for (int k = 2; k <= n; ++k) {
        vector<int> available;
        for (int i = 1; i <= n; ++i) {
            if (!position_filled[i]) available.push_back(i);
        }

        if (available.empty()) break; 
        
        // Binary search to find which available slot holds k
        int low = 0, high = available.size() - 1;
        while (low < high) {
            int mid = low + (high - low) / 2;
            
            vector<int> q(n);
            // Construct query:
            // - Known positions filled with their correct values (matches)
            // - Candidate positions (low..mid) filled with k (match if correct)
            // - Other unknown positions filled with 1 (no match guaranteed)
            for (int i = 1; i <= n; ++i) {
                if (position_filled[i]) {
                    q[i-1] = p_ans[i];
                } else {
                    q[i-1] = 1; 
                }
            }
            // Override candidates with k
            for (int i = low; i <= mid; ++i) {
                q[available[i]-1] = k;
            }

            int score = query(q);
            // Matches from fixed positions: k-1
            // If pos(k) is in candidates, total score = k.
            // If pos(k) is not in candidates, total score = k-1.
            
            if (score == k) {
                high = mid;
            } else {
                low = mid + 1;
            }
        }
        p_ans[available[low]] = k;
        position_filled[available[low]] = true;
    }

    // Output result
    vector<int> res;
    for (int i = 1; i <= n; ++i) res.push_back(p_ans[i]);
    guess(res);

    return 0;
}