#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

using namespace std;

// Maximum n is 20, so n^2 <= 400.
// We use an adjacency list to store the "defeated by" relationship (children in the tree).
vector<int> adj[405];

// Helper to perform the interaction query
int query(const vector<int>& v) {
    cout << "?";
    for (int x : v) cout << " " << x;
    cout << endl; // endl forces flush
    int res;
    cin >> res;
    return res;
}

void solve() {
    int n;
    if (!(cin >> n)) return;
    int N = n * n;
    
    // Clear adjacency lists for the current test case
    for (int i = 1; i <= N; ++i) {
        adj[i].clear();
    }
    
    // Initially, all pepes are roots of trivial trees
    vector<int> roots(N);
    iota(roots.begin(), roots.end(), 1);
    
    // We need to output the n^2 - n + 1 fastest pepes
    int to_output = N - n + 1;
    vector<int> result;
    result.reserve(to_output);
    
    // Repeatedly extract the maximum element
    while (result.size() < to_output) {
        // While we have more than one candidate for the current maximum,
        // we perform races to reduce the number of candidates.
        while (roots.size() > 1) {
            int k = roots.size();
            // We can race at most n pepes at once
            int take = min(k, n);
            
            vector<int> participants;
            participants.reserve(n);
            
            // Select the first 'take' roots to participate
            for (int i = 0; i < take; ++i) {
                participants.push_back(roots[i]);
            }
            
            // Keep a copy of the roots involved in this race to handle logic after query
            vector<int> race_roots = participants;
            
            // If we don't have enough roots to form a full race of n pepes,
            // we must fill the remaining spots with 'filler' pepes.
            // These fillers must be known to be slower than the candidates to avoid affecting the result.
            // We use descendants of the current race_roots (who have lost to them or their ancestors previously).
            if (take < n) {
                vector<int> stack;
                // Add immediate children of current participants to search for descendants
                for (int r : race_roots) {
                    for (auto it = adj[r].rbegin(); it != adj[r].rend(); ++it) {
                        stack.push_back(*it);
                    }
                }
                
                // Collect enough descendants to reach n participants
                while (participants.size() < n && !stack.empty()) {
                    int u = stack.back();
                    stack.pop_back();
                    participants.push_back(u);
                    
                    // Add children of u to continue search if needed
                    for (auto it = adj[u].rbegin(); it != adj[u].rend(); ++it) {
                        stack.push_back(*it);
                    }
                }
            }
            
            // Perform the race
            int winner = query(participants);
            
            // Remove the participating roots from the roots list
            roots.erase(roots.begin(), roots.begin() + take);
            
            // The winner remains a candidate (root)
            roots.push_back(winner);
            
            // The losers among the roots become children of the winner
            for (int r : race_roots) {
                if (r != winner) {
                    adj[winner].push_back(r);
                }
            }
        }
        
        // Now roots contains exactly 1 element, which is the global maximum among current candidates
        int best = roots[0];
        result.push_back(best);
        roots.clear();
        
        // Promote the children of the best pepe to be new candidates
        for (int child : adj[best]) {
            roots.push_back(child);
        }
    }
    
    // Output the result
    cout << "!";
    for (int x : result) cout << " " << x;
    cout << endl;
}

int main() {
    // Optimize standard I/O operations
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