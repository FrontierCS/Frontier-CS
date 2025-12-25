#include <iostream>
#include <vector>
#include <numeric>
#include <string>

using namespace std;

void solve() {
    int n;
    if (!(cin >> n)) return;

    // s0: Candidates for whom the previous answer was (or is assumed) truthful.
    // s1: Candidates for whom the previous answer was a lie.
    vector<int> s0(n);
    iota(s0.begin(), s0.end(), 1);
    vector<int> s1;

    // We can make up to 53 queries.
    for (int query = 0; query < 53; ++query) {
        // If we have reduced to <= 2 candidates, we can use our 2 guesses.
        if (s0.size() + s1.size() <= 2) break;

        // Split both sets roughly in half to balance the reduction.
        int n0 = s0.size();
        int n1 = s1.size();
        int k = n0 / 2; // Part A of s0
        int p = n1 / 2; // Part C of s1

        // Query set Q = A u C
        vector<int> q_set;
        q_set.reserve(k + p);
        for(int i = 0; i < k; ++i) q_set.push_back(s0[i]);
        for(int i = 0; i < p; ++i) q_set.push_back(s1[i]);

        cout << "? " << q_set.size();
        for (int x : q_set) cout << " " << x;
        cout << endl;

        string ans;
        cin >> ans;

        vector<int> next_s0, next_s1;
        next_s0.reserve(n0 + n1);
        next_s1.reserve(n0 + n1);

        if (ans == "YES") {
            // YES implies x in Q.
            // For A (s0 in Q): Consistent. Stays s0.
            // For C (s1 in Q): Consistent. Becomes s0 (lie streak broken).
            // For B (s0 not in Q): Inconsistent. Becomes s1 (assumed lie).
            // For D (s1 not in Q): Inconsistent. Since previously lie, now MUST be true.
            //    If x in D, truth is NO (x not in Q). Judge said YES. Lie. 
            //    Two consecutive lies impossible -> x cannot be in D. Eliminated.
            
            // A -> s0
            for(int i = 0; i < k; ++i) next_s0.push_back(s0[i]);
            // C -> s0
            for(int i = 0; i < p; ++i) next_s0.push_back(s1[i]);
            // B -> s1
            for(int i = k; i < n0; ++i) next_s1.push_back(s0[i]);
        } else {
            // NO implies x not in Q.
            // For B (s0 not in Q): Consistent. Stays s0.
            // For D (s1 not in Q): Consistent. Becomes s0.
            // For A (s0 in Q): Inconsistent. Becomes s1.
            // For C (s1 in Q): Inconsistent. Two consecutive lies impossible -> Eliminated.

            // B -> s0
            for(int i = k; i < n0; ++i) next_s0.push_back(s0[i]);
            // D -> s0
            for(int i = p; i < n1; ++i) next_s0.push_back(s1[i]);
            // A -> s1
            for(int i = 0; i < k; ++i) next_s1.push_back(s0[i]);
        }
        s0 = next_s0;
        s1 = next_s1;
    }

    // Collect remaining candidates
    vector<int> candidates = s0;
    candidates.insert(candidates.end(), s1.begin(), s1.end());

    // Guess them
    for(int x : candidates) {
        cout << "! " << x << endl;
        string res;
        cin >> res;
        if (res == ":)") return;
        // If ":(", proceed to next guess
    }
}

int main() {
    // Optimization not strictly necessary but good practice.
    // endl flushes stream, so interaction works.
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    solve();
    return 0;
}