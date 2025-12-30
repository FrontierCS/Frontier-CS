#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <random>

using namespace std;

// Global variables
int n;
vector<int> p;
vector<int> pos_of_val;

// Helper to interact with the system
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

// Helper to output answer
void answer(const vector<int>& ans) {
    cout << "1";
    for (int x : ans) {
        cout << " " << x;
    }
    cout << endl;
    exit(0);
}

int main() {
    // Optimization for faster I/O
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> n)) return 0;

    p.assign(n, 0);
    pos_of_val.assign(n + 1, -1);
    
    // Initial unknown indices
    vector<int> u(n);
    iota(u.begin(), u.end(), 0);

    // Trivial case n=1
    if (n == 1) {
        answer({1});
    }

    // Random number generator
    mt19937 rng(1337);

    // Step 1: Find position of 1
    // We do binary search on the set of candidate indices.
    // Since we don't have a "safe" filler value yet (we don't know any positions),
    // we use a randomized strategy to distinguish which half 1 is in.
    vector<int> candidates = u;
    
    while (candidates.size() > 1) {
        int sz = candidates.size();
        int mid = sz / 2;
        vector<int> L, R;
        L.reserve(mid);
        R.reserve(sz - mid);
        for(int i=0; i<mid; ++i) L.push_back(candidates[i]);
        for(int i=mid; i<sz; ++i) R.push_back(candidates[i]);

        bool found_split = false;
        while (!found_split) {
            // Pick random filler f from 2..n
            int f = 2 + (rng() % (n - 1));
            
            // Construct query:
            // Fill L with 1
            // Fill R with f
            // Fill all other indices with 1
            // Logic:
            // Matches from 1: If pos[1] in L or Others, match=1. If pos[1] in R, match=0.
            // Matches from f: If pos[f] in R, match=1. If pos[f] in L or Others, match=0.
            // Possibilities:
            // 1 in L/Others, f in L/Others: Score 1
            // 1 in L/Others, f in R: Score 2
            // 1 in R, f in L/Others: Score 0
            // 1 in R, f in R: Score 1
            // So Score 2 => 1 in L (candidates = L)
            // Score 0 => 1 in R (candidates = R)
            // Score 1 => Ambiguous, retry with different f
            
            vector<int> q(n, 1); 
            for(int idx : R) q[idx] = f;
            
            int s = query(q);
            if (s == 2) {
                candidates = L;
                found_split = true;
            } else if (s == 0) {
                candidates = R;
                found_split = true;
            }
        }
    }
    
    int pos1 = candidates[0];
    p[pos1] = 1;
    pos_of_val[1] = pos1;
    
    // Remove pos1 from unknown indices u
    vector<int> next_u;
    next_u.reserve(n-1);
    for(int idx : u) {
        if(idx != pos1) next_u.push_back(idx);
    }
    u = next_u;
    
    // Step 2: Find positions of 2..n-1
    // Now we have a safe filler: value 1.
    // Since we know where 1 is, and for all currently unknown indices the value is > 1,
    // putting 1 in unknown spots yields 0 matches.
    for (int k = 2; k < n; ++k) {
        vector<int> cur_candidates = u;
        while (cur_candidates.size() > 1) {
            int sz = cur_candidates.size();
            int mid = sz / 2;
            vector<int> L, R;
            L.reserve(mid);
            for(int i=0; i<mid; ++i) L.push_back(cur_candidates[i]);
            for(int i=mid; i<sz; ++i) R.push_back(cur_candidates[i]);
            
            // Query construction:
            // 1. Known positions 1..k-1 filled with correct values.
            // 2. L filled with k.
            // 3. R (and other unknowns) filled with 1.
            // 4. Note: p array has 0 for unknowns. We construct q based on this.
            
            vector<int> q(n, 1); // Default filler 1
            for (int v = 1; v < k; ++v) {
                q[pos_of_val[v]] = v;
            }
            for (int idx : L) {
                q[idx] = k;
            }
            
            // Expected matches:
            // From knowns: k - 1 matches.
            // From 1-filler in R/Others: 0 matches (since unknowns are >= k > 1).
            // From k in L: 1 match if pos[k] in L, else 0.
            
            int s = query(q);
            if (s == k) { // (k-1) + 1 match
                cur_candidates = L;
            } else { // (k-1) + 0 matches
                cur_candidates = R;
            }
        }
        
        int posk = cur_candidates[0];
        p[posk] = k;
        pos_of_val[k] = posk;
        
        // Remove found index from u
        vector<int> nu;
        nu.reserve(u.size()-1);
        for(int idx : u) {
            if(idx != posk) nu.push_back(idx);
        }
        u = nu;
    }
    
    // The last remaining position must be n
    if (!u.empty()) {
        p[u[0]] = n;
    }
    
    answer(p);
    
    return 0;
}