#include <iostream>
#include <vector>
#include <algorithm>

using namespace std;

// Function to perform a race query.
// It prints the query in the specified format and reads the winner.
int query(const vector<int>& p) {
    cout << "?";
    for (int x : p) cout << " " << x;
    cout << endl;
    int res;
    cin >> res;
    return res;
}

void solve() {
    int n;
    // Read n, break if input fails
    if (!(cin >> n)) return;

    // Tree structure: children[u] contains all pepes known to be slower than u directly.
    // We use a vector of vectors (adjacency list) to represent the tree/forest logic.
    // Nodes are 1-indexed, so size is n*n + 1.
    vector<vector<int>> children(n * n + 1);
    
    // active_roots contains the current candidates for the global maximum.
    // Initially, we will populate this by winning groups.
    vector<int> active_roots;
    
    // Step 1: Initial Partition
    // Divide the n^2 pepes into n groups of n. Race each group.
    // The winners become the initial roots. The losers attach to their group's winner.
    int cnt = 1;
    for (int i = 0; i < n; ++i) {
        vector<int> group;
        for (int j = 0; j < n; ++j) {
            group.push_back(cnt++);
        }
        int winner = query(group);
        active_roots.push_back(winner);
        for (int x : group) {
            if (x != winner) {
                children[winner].push_back(x);
            }
        }
    }

    vector<int> result;
    // We need to find the top n^2 - n + 1 fastest pepes in order.
    // The remaining n-1 are indistinguishable slowest ones.
    int target_count = n * n - n + 1;

    for (int k = 0; k < target_count; ++k) {
        // While we have more than 1 candidate root, we need to narrow it down to 1.
        // We do this by racing subsets of roots.
        while (active_roots.size() > 1) {
            vector<int> race;
            vector<int> participating_roots;
            
            // Pick up to n roots to participate in the race.
            int roots_to_pick = min((int)active_roots.size(), n);
            for (int i = 0; i < roots_to_pick; ++i) {
                race.push_back(active_roots[i]);
                participating_roots.push_back(active_roots[i]);
            }

            // If we selected fewer than n roots (because active_roots.size() < n),
            // we must fill the race spots with "dummy" participants to reach size n.
            // We use descendants of the participating roots as fillers because
            // we already know they are slower than their ancestors, so they won't disturb the
            // relative order of the roots.
            if (race.size() < n) {
                int needed = n - race.size();
                for (int r : participating_roots) {
                    if (needed == 0) break;
                    // Use BFS to find descendants to use as fillers
                    vector<int> q;
                    q.push_back(r);
                    size_t head = 0;
                    while(head < q.size() && needed > 0) {
                        int u = q[head++];
                        for(int c : children[u]) {
                            race.push_back(c);
                            needed--;
                            if (needed == 0) break;
                            q.push_back(c);
                        }
                    }
                }
            }

            // Perform the race
            int w = query(race);

            // Update the set of active_roots:
            // 1. Remove the roots that participated from the list.
            // 2. Add the winner back to the list.
            // 3. The roots that lost become children of the winner.
            
            vector<int> next_roots;
            // Keep roots that did not participate in this race
            for(size_t i = roots_to_pick; i < active_roots.size(); ++i) {
                next_roots.push_back(active_roots[i]);
            }
            
            // Add the winner
            next_roots.push_back(w);
            
            // Attach losers
            for (int r : participating_roots) {
                if (r != w) {
                    children[w].push_back(r);
                }
            }
            
            active_roots = next_roots;
        }

        // Now active_roots has exactly 1 element. This is the global maximum among remaining.
        int best = active_roots[0];
        result.push_back(best);
        
        // Remove 'best' from the system.
        // Its direct children now become candidates for the next maximum (new roots).
        active_roots.clear();
        for (int c : children[best]) {
            active_roots.push_back(c);
        }
    }

    // Output the result
    cout << "!";
    for (int x : result) cout << " " << x;
    cout << endl;
}

int main() {
    // Fast I/O is less critical for interactive problems but good practice.
    // However, we rely on automatic flushing or manual flushing.
    int t;
    if (cin >> t) {
        while (t--) {
            solve();
        }
    }
    return 0;
}