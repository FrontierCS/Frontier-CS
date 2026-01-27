#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <set>

using namespace std;

void solve() {
    int n;
    if (!(cin >> n)) return;

    int n2 = n * n;
    vector<vector<int>> Q(n);
    vector<int> current_pepes(n2);
    iota(current_pepes.begin(), current_pepes.end(), 1);

    // Initial distribution
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            Q[i].push_back(current_pepes[i * n + j]);
        }
    }

    vector<int> S(n); // Representatives in the final race
    vector<int> owner(n2 + 1, -1); // Tracks which bucket a representative came from

    // Initial races to find bucket leaders
    for (int i = 0; i < n; ++i) {
        cout << "?";
        for (int x : Q[i]) cout << " " << x;
        cout << endl;
        int winner;
        cin >> winner;
        S[i] = winner;
        
        // Remove winner from Q[i]
        vector<int> next_Q;
        for(int x : Q[i]) if(x != winner) next_Q.push_back(x);
        Q[i] = next_Q;
    }

    int total_output = n2 - n + 1;
    vector<int> result;
    
    // We assume S is always full (size n).
    // Some elements in S might be dummies if their bucket Q[i] is effectively empty or dominated.
    // However, for the logic, we maintain distinct candidates in S.
    // Since we stop when n-1 elements remain, we theoretically always have >= n elements available.
    
    for (int step = 0; step < total_output; ++step) {
        // Query S
        cout << "?";
        for (int x : S) cout << " " << x;
        cout << endl;
        
        int winner;
        cin >> winner;
        result.push_back(winner);

        if (step == total_output - 1) break;

        // Find which slot the winner belonged to
        int k = -1;
        for (int i = 0; i < n; ++i) {
            if (S[i] == winner) {
                k = i;
                break;
            }
        }

        // We need to refill S[k] from Q[k].
        // If Q[k] is empty, we must pick a dummy.
        // A dummy should be an element guaranteed to lose.
        // We can pick any element from Q[j] where j != k and Q[j] is not empty.
        // Ideally Q[j] corresponds to a valid suppressor S[j].
        
        if (Q[k].empty()) {
            // Pick a dummy from another bucket
            bool found = false;
            for (int j = 0; j < n; ++j) {
                if (j != k && !Q[j].empty()) {
                    S[k] = Q[j].back(); // Just a copy, acts as dummy
                    found = true;
                    break;
                }
            }
            // If not found, it means all Q are empty. 
            // This implies we are at the very end of process (only S elements remain).
            // But we check loop condition, total_output logic ensures we don't query invalidly.
            // If we are here, we must have found something or loop ends.
            // Actually, if all Q empty, we have exactly n items left (in S).
            // We just outputted one. n-1 left. Loop should break.
            // But let's keep robust.
        } else {
            // Try to find a new max from Q[k].
            // We need to race Q[k] against a suppressor to filter out non-maxes efficiently
            // or just to fill the query size.
            // Suppressors: candidates in S other than slot k.
            
            // Collect all available elements to form a race of size n.
            // Essential participants: Q[k]
            // Suppressors: S[j] (j != k)
            // Padding: Q[j]
            
            vector<int> race_participants;
            for (int x : Q[k]) race_participants.push_back(x);
            
            // We need to fill up to n.
            // We add pairs of (S[j], data from Q[j])
            for (int j = 0; j < n; ++j) {
                if (j == k) continue;
                if (race_participants.size() == n) break;
                
                // Add suppressor S[j]
                race_participants.push_back(S[j]);
                if (race_participants.size() == n) break;
                
                // Add padding from Q[j]
                for (int x : Q[j]) {
                    // Avoid duplicates if S[k] was previously a dummy from Q[j] (though now S[k] is being replaced)
                    // Also S currently contains unique IDs for query S, but here we build a new query.
                    // Just ensure distinctness.
                    // race_participants vector check
                    bool exists = false;
                    for(int existing : race_participants) if(existing == x) exists = true;
                    if(!exists) {
                        race_participants.push_back(x);
                        if (race_participants.size() == n) break;
                    }
                }
            }
            
            cout << "?";
            for (int x : race_participants) cout << " " << x;
            cout << endl;
            
            int sub_winner;
            cin >> sub_winner;
            
            // Check if sub_winner corresponds to a suppressor
            bool suppressor_won = false;
            for (int j = 0; j < n; ++j) {
                if (j != k && S[j] == sub_winner) {
                    suppressor_won = true;
                    break;
                }
            }
            
            if (suppressor_won) {
                // The candidate from Q[k] is weaker than S[j].
                // We don't have a strong candidate for S[k].
                // Use a dummy from Q[k].
                S[k] = Q[k].back();
            } else {
                // A new candidate from Q[k] won.
                S[k] = sub_winner;
                // Remove it from Q[k]
                vector<int> next_Q;
                for(int x : Q[k]) if(x != sub_winner) next_Q.push_back(x);
                Q[k] = next_Q;
            }
        }
    }

    cout << "!";
    for (int x : result) cout << " " << x;
    cout << endl;
}

int main() {
    int t;
    if (cin >> t) {
        while (t--) {
            solve();
        }
    }
    return 0;
}