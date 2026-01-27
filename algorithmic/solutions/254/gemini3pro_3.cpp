#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

using namespace std;

// Function to perform a query
// Prints "? x1 x2 ... xn" and reads the winner
int query(const vector<int>& indices) {
    cout << "?";
    for (int x : indices) {
        cout << " " << x;
    }
    cout << endl;
    int winner;
    cin >> winner;
    return winner;
}

void solve() {
    int n;
    if (!(cin >> n)) return;

    int N = n * n;
    vector<int> S; // Current leaders (candidates for global maximum)
    vector<vector<int>> bags(N + 1); // Indices 1 to N. bags[u] stores elements dominated by u.

    // Initial setup: Partition N pepes into n groups of n.
    // For each group, find the winner and add to S. Losers go to winner's bag.
    int current_pepe = 1;
    for (int i = 0; i < n; ++i) {
        vector<int> group;
        for (int j = 0; j < n; ++j) {
            group.push_back(current_pepe++);
        }
        int winner = query(group);
        S.push_back(winner);
        for (int x : group) {
            if (x != winner) {
                bags[winner].push_back(x);
            }
        }
    }

    vector<int> result;
    // We need to determine the fastest n^2 - n + 1 pepes.
    int target_count = N - n + 1;

    for (int step = 0; step < target_count; ++step) {
        // 1. Find the global winner among current leaders S.
        int winner;
        if (S.size() == n) {
            // We have exactly n leaders, query them directly.
            winner = query(S);
        } else {
            // We have fewer than n leaders. We need to pad the query with 'known losers'.
            // Padding elements can be taken from the bags of current leaders.
            // Since total remaining elements >= n (because we still need to output),
            // and orphans are empty at this stage, the leaders + their bags cover all remaining elements.
            // Thus, we definitely have enough elements to pad.
            vector<int> q = S;
            int needed = n - S.size();
            for (int leader : S) {
                if (needed == 0) break;
                int take = min((int)bags[leader].size(), needed);
                for (int k = 0; k < take; ++k) {
                    q.push_back(bags[leader][k]);
                }
                needed -= take;
            }
            winner = query(q);
        }
        
        result.push_back(winner);
        
        // Remove the winner from S.
        auto it = find(S.begin(), S.end(), winner);
        S.erase(it);

        // 2. Process orphans.
        // The elements in the winner's bag are no longer dominated by anyone in S.
        // We must re-integrate them into the system (either make them leaders or put into another bag).
        vector<int> orphans = bags[winner];
        bags[winner].clear(); 

        while (!orphans.empty()) {
            if (S.empty()) {
                // If S is empty, we must promote some orphans to S.
                // We take a batch of orphans and race them.
                int batch_size = min((int)orphans.size(), n);
                vector<int> batch;
                for(int k=0; k<batch_size; ++k) {
                    batch.push_back(orphans.back());
                    orphans.pop_back();
                }
                
                int w = query(batch);
                S.push_back(w);
                for(int x : batch) {
                    if (x != w) bags[w].push_back(x);
                }
            } else {
                // S is not empty. We can race a batch of orphans against an existing leader `u`.
                // This helps to either filter orphans (if u wins) or replace u (if an orphan wins).
                int u = S.back();
                
                int batch_size = min((int)orphans.size(), n - 1);
                vector<int> batch;
                for(int k=0; k<batch_size; ++k) {
                    batch.push_back(orphans.back());
                    orphans.pop_back();
                }
                
                vector<int> q = batch;
                q.push_back(u);
                
                int w = query(q);
                
                if (w == u) {
                    // u is faster than all orphans in the batch.
                    // They become dominated by u.
                    for(int x : batch) bags[u].push_back(x);
                } else {
                    // One of the orphans (w) is faster than u (and the rest of the batch).
                    // w replaces u in S.
                    // u and its bag become dominated by w.
                    S.pop_back(); // Remove u
                    S.push_back(w); // Add w
                    
                    // Move u and its bag to w
                    bags[w].push_back(u);
                    bags[w].insert(bags[w].end(), bags[u].begin(), bags[u].end());
                    bags[u].clear();
                    
                    // The other losers in the batch also go to w
                    for(int x : batch) {
                        if (x != w) bags[w].push_back(x);
                    }
                }
            }
        }
    }

    // Output the result
    cout << "!";
    for (int p : result) {
        cout << " " << p;
    }
    cout << endl;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    int t;
    if (cin >> t) {
        while (t--) {
            solve();
        }
    }
    return 0;
}