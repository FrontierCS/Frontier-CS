#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <random>

using namespace std;

// Function to check if the goal state is reached (every player i has only cards with value i)
bool is_solved(int n, const vector<vector<int>>& cards) {
    for (int i = 1; i <= n; ++i) {
        for (int c : cards[i]) {
            if (c != i) return false;
        }
    }
    return true;
}

// Kuhn's algorithm for Maximum Bipartite Matching
// dfs function to find augmenting path
bool dfs(int u, const vector<vector<int>>& adj, vector<int>& matchR, vector<bool>& vis) {
    for (int v : adj[u]) {
        if (vis[v]) continue;
        vis[v] = true;
        if (matchR[v] < 0 || dfs(matchR[v], adj, matchR, vis)) {
            matchR[v] = u;
            return true;
        }
    }
    return false;
}

int main() {
    // optimize I/O
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    if (!(cin >> n)) return 0;

    // 1-based indexing for players
    vector<vector<int>> cards(n + 1);
    for (int i = 1; i <= n; ++i) {
        for (int j = 0; j < n; ++j) {
            int c;
            cin >> c;
            cards[i].push_back(c);
        }
    }

    struct Operation {
        vector<int> moves;
    };
    vector<Operation> history;

    // Constraint is N^2 - N. We set a limit slightly higher to be safe in loop, 
    // but the logic targets convergence well within limits.
    int max_ops = n * n; 

    // Random number generator for shuffling preferences
    mt19937 rng(1337);

    while (!is_solved(n, cards) && (int)history.size() < max_ops) {
        // Construct bipartite graph for matching
        // Left: Players 1..n
        // Right: Card Values 1..n
        // Edge u -> v exists if Player u holds a card of value v.
        vector<vector<int>> adj(n + 1);
        for (int i = 1; i <= n; ++i) {
            // Get unique values held by player i
            vector<int> vals = cards[i];
            sort(vals.begin(), vals.end());
            vals.erase(unique(vals.begin(), vals.end()), vals.end());
            
            // Heuristic: Prefer passing card v != i.
            // This reduces the distance of card v to its target player v.
            // If we keep v == i, it's fine, but we are forced to pass something.
            // We sort the adjacency list so that non-diagonal edges (v != i) come first.
            vector<int> sorted_vals;
            bool has_self = false;
            for (int v : vals) {
                if (v == i) has_self = true;
                else sorted_vals.push_back(v);
            }
            // Shuffle non-diagonal edges to avoid deterministic loops
            shuffle(sorted_vals.begin(), sorted_vals.end(), rng);
            
            // Add self-edge last (lowest priority)
            if (has_self) sorted_vals.push_back(i);
            
            adj[i] = sorted_vals;
        }

        // Find a perfect matching using Kuhn's algorithm with greedy initialization
        // matchR[v] stores the player u who passes value v
        vector<int> matchR(n + 1, -1);
        
        // Greedy initialization phase
        // Try to match using random order of players to speed up
        vector<int> p(n);
        iota(p.begin(), p.end(), 1);
        shuffle(p.begin(), p.end(), rng);
        
        vector<bool> usedR(n + 1, false);
        for(int u : p) {
            for(int v : adj[u]) {
                if(!usedR[v]) {
                    usedR[v] = true;
                    matchR[v] = u;
                    break;
                }
            }
        }

        // DFS phase for unmatched nodes
        // Identify which Left nodes (Players) are not matched
        vector<bool> matchedL(n + 1, false);
        for(int v = 1; v <= n; ++v) {
            if(matchR[v] != -1) matchedL[matchR[v]] = true;
        }

        vector<bool> vis(n + 1);
        for (int i = 1; i <= n; ++i) {
            if (!matchedL[i]) {
                fill(vis.begin(), vis.end(), false);
                dfs(i, adj, matchR, vis);
            }
        }
        
        // Reconstruct the moves for each player
        // matchL[u] = v means Player u passes value v
        vector<int> matchL(n + 1, 0);
        for(int v = 1; v <= n; ++v) {
            if (matchR[v] != -1) matchL[matchR[v]] = v;
        }

        // Store history
        vector<int> current_moves(n);
        for(int i = 1; i <= n; ++i) {
            current_moves[i-1] = matchL[i];
        }
        history.push_back({current_moves});

        // Execute moves: remove passed cards
        for(int i = 1; i <= n; ++i) {
            int val_to_remove = matchL[i];
            auto it = find(cards[i].begin(), cards[i].end(), val_to_remove);
            cards[i].erase(it);
        }
        
        // Execute moves: receive cards
        for(int i = 1; i <= n; ++i) {
            int val_passed = matchL[i]; 
            int receiver = (i % n) + 1; // Passes to right
            cards[receiver].push_back(val_passed);
        }
    }

    // Output results
    cout << history.size() << "\n";
    for (const auto& op : history) {
        for (int i = 0; i < n; ++i) {
            cout << op.moves[i] << (i == n - 1 ? "" : " ");
        }
        cout << "\n";
    }

    return 0;
}