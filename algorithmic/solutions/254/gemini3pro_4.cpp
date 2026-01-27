#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

using namespace std;

// Function to perform a query
int query(const vector<int>& p) {
    cout << "?";
    for (int x : p) {
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

    int total_pepes = n * n;
    vector<int> roots(total_pepes);
    iota(roots.begin(), roots.end(), 1); // Fill with 1, 2, ..., n^2

    // Adjacency list to store the tree of defeated opponents (children)
    // children[u] contains all v such that u defeated v directly in a race where u was the winner
    // and u was subsequently not defeated (until u is output).
    vector<vector<int>> children(total_pepes + 1);
    
    vector<int> result;
    int target_count = total_pepes - n + 1;

    while (result.size() < target_count) {
        // Reduction phase: Reduce the number of roots to <= n
        while (roots.size() > n) {
            vector<int> race_participants;
            // Take n roots from the back
            for (int i = 0; i < n; ++i) {
                race_participants.push_back(roots.back());
                roots.pop_back();
            }
            
            int winner = query(race_participants);
            
            // The winner returns to roots, others become children of the winner
            roots.push_back(winner);
            for (int p : race_participants) {
                if (p != winner) {
                    children[winner].push_back(p);
                }
            }
        }

        // Output phase: Find the max among current roots
        int winner = -1;
        
        // If we have only 1 root, it is the max.
        // If we have > 1 roots (and size <= n), we must race them to find the max.
        // If roots.size() < n, we need to pad the query with known non-maximal elements (descendants).
        
        if (roots.size() == 1) {
            winner = roots[0];
            roots.pop_back();
        } else {
            vector<int> race_participants = roots;
            roots.clear();
            
            // Prepare the query vector
            vector<int> current_query = race_participants;
            
            // Add padding if needed
            if (current_query.size() < n) {
                int needed = n - current_query.size();
                // Collect padding from descendants of the race participants
                vector<int> padding;
                for (int r : race_participants) {
                    if (padding.size() >= needed) break;
                    
                    // Simple DFS to find descendants
                    vector<int> stack = children[r];
                    while (!stack.empty()) {
                        int curr = stack.back();
                        stack.pop_back();
                        padding.push_back(curr);
                        if (padding.size() >= needed) break;
                        
                        for (int c : children[curr]) {
                            stack.push_back(c);
                        }
                    }
                }
                current_query.insert(current_query.end(), padding.begin(), padding.end());
            }
            
            winner = query(current_query);
            
            // The winner is identified.
            // All other participants in the race (excluding padding) become children of the winner.
            // Padding elements do not change their parent pointers as they are already descendants.
            
            for (int p : race_participants) {
                if (p != winner) {
                    children[winner].push_back(p);
                }
            }
        }

        result.push_back(winner);
        
        // Promote children of the winner to be new roots
        for (int c : children[winner]) {
            roots.push_back(c);
        }
        // Clear children of winner to release memory/avoid confusion
        children[winner].clear();
    }

    cout << "!";
    for (int x : result) {
        cout << " " << x;
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