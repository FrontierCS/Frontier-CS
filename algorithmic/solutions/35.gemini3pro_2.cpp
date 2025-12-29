#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <random>

using namespace std;

int N;
mt19937 rng(1337);

// Perform a query. Returns 1 if x is in the subset of indices S, 0 otherwise.
int query(int x, const vector<int>& S) {
    if (S.empty()) return 0;
    cout << "? " << x << " " << S.size();
    for (int s : S) {
        cout << " " << s;
    }
    cout << endl;
    int res;
    cin >> res;
    if (res == -1) exit(0);
    return res;
}

// Recursive solver.
// Returns the unique number if found in 'candidates', or -1 if not found.
int solve(vector<int>& candidates) {
    if (candidates.empty()) return -1;
    
    // Base case: single candidate. Verify it's not a duplicate.
    if (candidates.size() == 1) {
        int x = candidates[0];
        // Perform a few checks to ensure x is not a duplicate that survived by chance.
        // A duplicate z has P_z = {u, v}. It is detected if we pick T such that u in T, v in ~T.
        // This happens with prob 0.5. 
        // With 7 checks, failure probability is 1/128, which is sufficient given prior filtering.
        for (int k = 0; k < 7; ++k) {
            vector<int> T, T_compl;
            for (int i = 1; i <= 2 * N - 1; ++i) {
                if (rng() % 2) T.push_back(i);
                else T_compl.push_back(i);
            }
            if (T.empty() || T_compl.empty()) continue; 
            
            int q1 = query(x, T);
            // If q1 is 0, x is in T_compl. Duplicate not split. Consistent.
            if (q1 == 0) continue;
            
            // If q1 is 1, x is in T. Check T_compl.
            int q2 = query(x, T_compl);
            if (q2 == 1) {
                // x is in T AND x is in T_compl => Split duplicate.
                return -1;
            }
        }
        return x;
    }

    // Recursive step
    // Generate random partition (S, S_compl)
    vector<int> S;
    vector<int> S_compl;
    for (int i = 1; i <= 2 * N - 1; ++i) {
        if (rng() % 2) {
            S.push_back(i);
        } else {
            S_compl.push_back(i);
        }
    }
    
    // Ensure neither is empty (very unlikely for N=300)
    if (S.empty() || S_compl.empty()) {
        S.clear(); S_compl.clear();
        S.push_back(1);
        for(int i=2; i<=2*N-1; ++i) S_compl.push_back(i);
    }

    vector<int> c0, c1;
    for (int x : candidates) {
        if (query(x, S)) {
            c1.push_back(x);
        } else {
            c0.push_back(x);
        }
    }

    // Priority to c0 because it implies P_x subset S_compl (stronger condition for duplicates)
    // and it is usually smaller or equal in size, but cleaner.
    int res = solve(c0);
    if (res != -1) return res;

    // If not found in c0, check c1.
    // Filter c1: elements must NOT be in S_compl.
    // If x in c1 AND x in S_compl => x is split duplicate.
    vector<int> c10;
    for (int x : c1) {
        if (!query(x, S_compl)) {
            c10.push_back(x);
        }
    }

    return solve(c10);
}

void run_test_case() {
    cin >> N;
    if (N == -1) exit(0);

    vector<int> candidates(N);
    iota(candidates.begin(), candidates.end(), 1);

    int ans = solve(candidates);
    cout << "! " << ans << endl;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    int t;
    if (cin >> t) {
        while (t--) {
            run_test_case();
        }
    }
    return 0;
}