#include <iostream>
#include <vector>
#include <numeric>
#include <cmath>
#include <cstdlib>
#include <algorithm>
#include <string>

using namespace std;

// Function to query the set S
// Returns true if answer is "YES", false if "NO"
bool query(const vector<int>& q) {
    // The problem requires a non-empty set.
    // Our logic ensures q is not empty inside the main loop.
    cout << "? " << q.size();
    for (int x : q) cout << " " << x;
    cout << endl;
    string resp;
    cin >> resp;
    return resp == "YES";
}

// Function to make a guess
// Terminates program if correct
void guess(int x) {
    cout << "! " << x << endl;
    string resp;
    cin >> resp;
    if (resp == ":)") {
        exit(0);
    }
    // If ":(", we continue
}

int main() {
    // Optimize standard I/O operations for speed
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    if (!(cin >> n)) return 0;

    // t0: Candidates consistent with the last answer being TRUTH (or initial state)
    // t1: Candidates consistent only if the last answer was a LIE
    vector<int> t0(n);
    iota(t0.begin(), t0.end(), 1);
    vector<int> t1;

    // Strategy: Minimize the potential function Phi = 2*|t0| + |t1|.
    // This potential roughly decreases by a factor of 0.75 each query on average.
    // We stop when total candidates <= 2, then use the 2 allowed guesses.
    while (t0.size() + t1.size() > 2) {
        int n0 = t0.size();
        int n1 = t1.size();
        
        int best_k0 = 0, best_k1 = 0;
        long long min_diff = -1;

        // We want to partition t0 into (k0, n0-k0) and t1 into (k1, n1-k1)
        // Query set Q will contain k0 elements from t0 and k1 from t1.
        // We aim to balance the resulting Potential in YES and NO cases.
        // Diff = |Phi_YES - Phi_NO| = |4*k0 + 8*k1 - (2*n0 + 4*n1)|
        // We iterate possible values of k1 and calculate optimal k0.
        
        for (int i = 0; i <= n1; ++i) {
            int k1 = i;
            // Solve 4*k0 approx 2*n0 + 4*n1 - 8*k1
            // k0 approx n0/2 + n1 - 2*k1
            int val = n0 / 2 + n1 - 2 * k1;
            
            // Check floor and ceil approximations since division truncates
            int candidates_k0[] = {val, val+1};
            
            for (int k0 : candidates_k0) {
                if (k0 < 0) k0 = 0;
                if (k0 > n0) k0 = n0;
                
                long long diff = abs(4LL * k0 + 8LL * k1 - (2LL * n0 + 4LL * n1));
                if (min_diff == -1 || diff < min_diff) {
                    min_diff = diff;
                    best_k0 = k0;
                    best_k1 = k1;
                }
            }
        }
        
        int k0 = best_k0;
        int k1 = best_k1;

        vector<int> q;
        q.reserve(k0 + k1);
        for (int i = 0; i < k0; ++i) q.push_back(t0[i]);
        for (int i = 0; i < k1; ++i) q.push_back(t1[i]);

        bool ans = query(q);

        vector<int> next_t0, next_t1;
        next_t0.reserve(n0 + n1); 
        next_t1.reserve(n0);

        if (ans) { // YES
            // Elements in Q match -> become t0 (consistent with Truth)
            for (int i = 0; i < k0; ++i) next_t0.push_back(t0[i]);
            for (int i = 0; i < k1; ++i) next_t0.push_back(t1[i]);
            // Elements in t0 not in Q mismatch -> become t1 (consistent only if Lie)
            for (int i = k0; i < n0; ++i) next_t1.push_back(t0[i]);
            // Elements in t1 not in Q mismatch -> eliminated (Lie -> Lie forbidden)
        } else { // NO
            // Elements not in Q match -> become t0 (consistent with Truth)
            for (int i = k0; i < n0; ++i) next_t0.push_back(t0[i]);
            for (int i = k1; i < n1; ++i) next_t0.push_back(t1[i]);
            // Elements in t0 inside Q mismatch -> become t1 (consistent only if Lie)
            for (int i = 0; i < k0; ++i) next_t1.push_back(t0[i]);
            // Elements in t1 inside Q mismatch -> eliminated (Lie -> Lie forbidden)
        }
        
        t0 = next_t0;
        t1 = next_t1;
    }

    // Combine remaining candidates
    vector<int> cands = t0;
    cands.insert(cands.end(), t1.begin(), t1.end());
    
    // Guess remaining candidates (at most 2)
    for (int x : cands) {
        guess(x);
    }
    
    return 0;
}