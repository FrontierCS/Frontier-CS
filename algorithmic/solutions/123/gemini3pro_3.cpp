#include <iostream>
#include <vector>
#include <string>
#include <algorithm>

using namespace std;

// Global vectors to hold the candidates
// s0: Candidates consistent with previous answer being Truth (or start)
// s1: Candidates consistent with previous answer being Lie (so next MUST be Truth)
vector<int> s0, s1;

// DP tables
// dp[i][j] stores the estimated minimum queries to solve state with |s0|=i, |s1|=j
// move_table[i][j] stores the optimal split {k0, k1}
// Table size sufficient for i + j <= 20
int dp[22][22];
pair<int, int> move_table[22][22];

// Precompute optimal moves for small total sizes
void precompute() {
    // Initialize DP table
    for (int i = 0; i < 22; ++i) {
        for (int j = 0; j < 22; ++j) {
            if (i + j <= 2) dp[i][j] = 0; // Can guess directly
            else dp[i][j] = 100; // Initialize with a high value
        }
    }

    // Value iteration to find optimal strategy
    for (int iter = 0; iter < 50; ++iter) {
        bool changed = false;
        // Iterate over all states with total size <= 20
        for (int i = 0; i <= 20; ++i) {
            for (int j = 0; j <= 20; ++j) {
                if (i + j > 20) continue; 
                if (i + j <= 2) continue; // Already solved
                
                int best_val = 100;
                pair<int, int> best_move = {-1, -1};

                // Try all valid splits (k0, k1) for query
                // We pick k0 from s0 (size i) and k1 from s1 (size j)
                // Q must be non-empty => k0 + k1 > 0
                for (int k0 = 0; k0 <= i; ++k0) {
                    for (int k1 = 0; k1 <= j; ++k1) {
                        if (k0 == 0 && k1 == 0) continue;

                        // Calculate next states sizes
                        // If YES:
                        // New s0 count: k0 (from s0) + k1 (from s1)
                        // New s1 count: i - k0 (from s0)
                        int ni_yes = k0 + k1;
                        int nj_yes = i - k0;
                        
                        // If NO:
                        // New s0 count: (i - k0) + (j - k1)
                        // New s1 count: k0
                        int ni_no = (i - k0) + (j - k1);
                        int nj_no = k0;

                        // Since total size never increases (sum <= i+j), bounds are safe
                        // Max queries = 1 + worst case of outcomes
                        int val = 1 + max(dp[ni_yes][nj_yes], dp[ni_no][nj_no]);
                        if (val < best_val) {
                            best_val = val;
                            best_move = {k0, k1};
                        }
                    }
                }
                
                if (best_val < dp[i][j]) {
                    dp[i][j] = best_val;
                    move_table[i][j] = best_move;
                    changed = true;
                }
            }
        }
        if (!changed) break;
    }
}

int main() {
    // Basic I/O setup
    // Use endl to flush output as required
    
    precompute();

    int n;
    if (!(cin >> n)) return 0;

    for (int i = 1; i <= n; ++i) {
        s0.push_back(i);
    }

    // Loop until we can guess (at most 2 candidates)
    while (s0.size() + s1.size() > 2) {
        int n0 = s0.size();
        int n1 = s1.size();
        int k0, k1;

        // Determine split strategy
        if (n0 + n1 <= 20) {
            // Use precomputed optimal move for small states
            // If somehow state is not computed (should not happen), fallback to heuristic
            if (dp[n0][n1] >= 100) {
                k0 = n0 / 2;
                k1 = n1 / 2;
                if (k0 == 0 && k1 == 0) k0 = 1;
            } else {
                k0 = move_table[n0][n1].first;
                k1 = move_table[n0][n1].second;
            }
        } else {
            // Heuristic for larger sizes: split both sets in half
            // This maximizes the flow of candidates into s1 or trash
            k0 = n0 / 2;
            k1 = n1 / 2;
            // Ensure non-empty query
            if (k0 == 0 && k1 == 0) k0 = 1; 
        }

        // Construct Query Set Q
        vector<int> Q;
        Q.reserve(k0 + k1);
        for (int i = 0; i < k0; ++i) Q.push_back(s0[i]);
        for (int i = 0; i < k1; ++i) Q.push_back(s1[i]);

        cout << "? " << Q.size();
        for (int x : Q) cout << " " << x;
        cout << endl;

        string ans;
        cin >> ans;

        vector<int> next_s0, next_s1;
        next_s0.reserve(n0 + n1);
        next_s1.reserve(n0);

        if (ans == "YES") {
            // Logic for YES:
            // Truth: x in Q. Lie: x not in Q.
            // s0 elements: if in Q, consistent with Truth -> s0. if not in Q, consistent with Lie -> s1.
            // s1 elements: if in Q, consistent with Truth -> s0. if not in Q, consistent with Lie -> IMPOSSIBLE (prev was Lie) -> Discard.
            
            // Elements in Q from s0 -> keep in s0
            for (int i = 0; i < k0; ++i) next_s0.push_back(s0[i]);
            // Elements in Q from s1 -> move to s0
            for (int i = 0; i < k1; ++i) next_s0.push_back(s1[i]);
            // Elements NOT in Q from s0 -> move to s1
            for (int i = k0; i < n0; ++i) next_s1.push_back(s0[i]);
        } else {
            // Logic for NO:
            // Truth: x not in Q. Lie: x in Q.
            // s0 elements: if not in Q, consistent with Truth -> s0. if in Q, consistent with Lie -> s1.
            // s1 elements: if not in Q, consistent with Truth -> s0. if in Q, consistent with Lie -> IMPOSSIBLE -> Discard.
            
            // Elements NOT in Q from s0 -> keep in s0
            for (int i = k0; i < n0; ++i) next_s0.push_back(s0[i]);
            // Elements NOT in Q from s1 -> move to s0
            for (int i = k1; i < n1; ++i) next_s0.push_back(s1[i]);
            // Elements in Q from s0 -> move to s1
            for (int i = 0; i < k0; ++i) next_s1.push_back(s0[i]);
        }

        s0 = next_s0;
        s1 = next_s1;
    }

    // Guess phase: we have at most 2 candidates
    vector<int> candidates = s0;
    candidates.insert(candidates.end(), s1.begin(), s1.end());

    // Try guesses. Guesses are reliable.
    for (int g : candidates) {
        cout << "! " << g << endl;
        string resp;
        cin >> resp;
        if (resp == ":)") return 0;
        // If response is :(, we proceed to the next candidate
        // Since x must be one of them, the last one will be correct.
    }

    return 0;
}