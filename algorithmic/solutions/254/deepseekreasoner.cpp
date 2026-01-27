/**
 * Pepe Racing Solution
 * 
 * Strategy:
 * 1. Maintain a set of "active roots" - candidates for the current fastest pepe.
 *    Initially, partition all n^2 pepes into groups of n, race them, and the winners become the initial active roots.
 *    The losers of each race become "followers" of the winner.
 * 
 * 2. To find the next fastest pepe:
 *    - If the number of active roots > n, perform reduction races. Take n roots, race them, keep the winner, 
 *      and make the losers followers of the winner. Repeat until |active roots| <= n.
 *    - Once |active roots| <= n, run a "final" race with all active roots.
 *      PAD the race with followers to reach size n. Followers are safe padding because they are known 
 *      to be slower than at least one current root (their leader).
 *    - The winner of this race is the global maximum. Output it.
 * 
 * 3. Remove the global maximum from active roots and promote all its direct followers to be new active roots.
 *    These followers were beaten only by the pepe we just outputted, so one of them could be the next fastest.
 * 
 * 4. Repeat until we have outputted n^2 - n + 1 pepes.
 * 
 * Complexity: Roughly O(N^2) queries, well within limits.
 */

#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

using namespace std;

// Function to query the interactor
// Prints "? x1 x2 ... xn" and returns the winner
int query(const vector<int>& participants) {
    cout << "?";
    for (int p : participants) {
        cout << " " << p;
    }
    cout << endl;
    int winner;
    cin >> winner;
    return winner;
}

void solve() {
    int n;
    cin >> n;
    
    int m = n * n;
    // We need to determine the fastest m - n + 1 pepes
    int target_count = m - n + 1;

    vector<int> active_roots;
    // followers[i] stores the list of pepes that lost directly to pepe i
    vector<vector<int>> followers(m + 1);
    
    // Initial population: create m pepes and form initial groups
    vector<int> pool(m);
    iota(pool.begin(), pool.end(), 1);
    
    // Initial reduction to get <= n candidates
    int current_idx = 0;
    while (current_idx + n <= m) {
        vector<int> batch;
        for (int i = 0; i < n; ++i) {
            batch.push_back(pool[current_idx + i]);
        }
        current_idx += n;
        
        int winner = query(batch);
        active_roots.push_back(winner);
        
        for (int p : batch) {
            if (p != winner) {
                followers[winner].push_back(p);
            }
        }
    }
    
    vector<int> result;
    
    for (int i = 0; i < target_count; ++i) {
        // Ensure the number of active candidates is not too large.
        // We need exactly n participants for a race, so if we have more candidates,
        // we must eliminate some by racing them against each other.
        while (active_roots.size() > n) {
            vector<int> batch;
            // Extract n candidates from the back
            for (int k = 0; k < n; ++k) {
                batch.push_back(active_roots.back());
                active_roots.pop_back();
            }
            
            int winner = query(batch);
            active_roots.push_back(winner);
            
            for (int p : batch) {
                if (p != winner) {
                    followers[winner].push_back(p);
                }
            }
        }
        
        // Now find the global max among active_roots.
        int best = -1;
        
        // If only one candidate remains, it must be the fastest among the remaining.
        if (active_roots.size() == 1) {
            best = active_roots[0];
        } else {
            // Need to determine the best among current roots (size between 2 and n).
            // We must form a race of exactly n participants.
            vector<int> batch = active_roots;
            int needed = n - batch.size();
            
            // Pad the race with followers. Followers are guaranteed to be smaller than their leaders.
            // Since all active roots are in the batch, and followers are dominated by these roots,
            // no follower can win.
            for (int r : active_roots) {
                if (needed == 0) break;
                for (int f : followers[r]) {
                    batch.push_back(f);
                    needed--;
                    if (needed == 0) break;
                }
            }
            
            best = query(batch);
        }
        
        result.push_back(best);
        
        // Remove best from active_roots
        auto it = find(active_roots.begin(), active_roots.end(), best);
        if (it != active_roots.end()) {
            active_roots.erase(it);
        }
        
        // Promote followers of the winner to be new candidates
        for (int f : followers[best]) {
            active_roots.push_back(f);
        }
        // Clear memory for the processed pepe
        vector<int>().swap(followers[best]);
    }
    
    // Output the result
    cout << "!";
    for (int p : result) {
        cout << " " << p;
    }
    cout << endl;
}

int main() {
    // Optimize I/O operations
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