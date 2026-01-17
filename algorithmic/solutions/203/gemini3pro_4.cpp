#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

using namespace std;

int N;
vector<vector<int>> adj;

// Function to send a query to the judge
int query(const vector<int>& p) {
    if (p.empty()) return 0;
    cout << "Query " << p.size();
    for (int x : p) cout << " " << x;
    cout << endl;
    int res;
    cin >> res;
    return res;
}

// Helper to count neighbors of u in a subset known to be an independent set
// For an independent set S, query(S) == |S|.
// If we query S U {u}, the number of distinct colors will be |S| + 1 - (number of neighbors of u in S).
// This formula works because each edge {u, v} with v in S reduces the distinct color count by 1.
// (Assuming u doesn't have multiple edges to the SAME node, which is impossible in simple graphs,
// and u connects to disjoint components in the interaction graph which are trivial single nodes here).
// Actually, for multiple neighbors, the formula holds because S is independent.
// Each neighbor v in S will either display C(u) (if v loves u) or u displays C(v) (if u loves v) or both C(u) (if same color).
// In all cases, the pair {u, v} effectively merges their contribution to colors.
// Since S is independent, interactions only happen between u and members of S.
int count_neighbors_in_set(const vector<int>& subset, int u) {
    if (subset.empty()) return 0;
    vector<int> q = subset;
    q.push_back(u);
    int res = query(q);
    return (int)subset.size() + 1 - res;
}

// Recursive function to find all neighbors of u in candidates
void find_neighbors(vector<int>& candidates, int u, vector<int>& found) {
    if (candidates.empty()) return;
    
    // Check total neighbors in this candidate set
    int k = count_neighbors_in_set(candidates, u);
    if (k == 0) return;
    
    if (candidates.size() == 1) {
        found.push_back(candidates[0]);
        return;
    }
    
    int mid = candidates.size() / 2;
    vector<int> left_part(candidates.begin(), candidates.begin() + mid);
    vector<int> right_part(candidates.begin() + mid, candidates.end());
    
    // Determine neighbors in left part
    int c_left = count_neighbors_in_set(left_part, u);
    
    if (c_left > 0) find_neighbors(left_part, u, found);
    // If there are remaining neighbors in the right part, search there
    if (k - c_left > 0) find_neighbors(right_part, u, found);
}

// Check if v is already a neighbor of u
bool is_nbr(int u, int v) {
    for (int x : adj[u]) if (x == v) return true;
    return false;
}

int main() {
    // No sync_with_stdio(false) due to interactive nature mixed with C++ streams (safer to default or flush manually)
    if (!(cin >> N)) return 0;
    
    int num_chameleons = 2 * N;
    adj.resize(num_chameleons + 1);
    
    // Store independent sets found so far (corresponding to a coloring of the graph)
    vector<vector<int>> independent_sets;
    
    // Phase 1: Build the graph
    for (int i = 1; i <= num_chameleons; ++i) {
        vector<int> neighbors;
        int placed_set_idx = -1;
        
        for (int j = 0; j < independent_sets.size(); ++j) {
            int c = count_neighbors_in_set(independent_sets[j], i);
            if (c > 0) {
                find_neighbors(independent_sets[j], i, neighbors);
            } else {
                // If no neighbors in this set, i can potentially belong to this set
                if (placed_set_idx == -1) placed_set_idx = j;
            }
        }
        
        for (int v : neighbors) {
            adj[i].push_back(v);
            adj[v].push_back(i);
        }
        
        if (placed_set_idx != -1) {
            independent_sets[placed_set_idx].push_back(i);
        } else {
            independent_sets.push_back({i});
        }
    }
    
    vector<int> love(num_chameleons + 1, 0); // love[u] = v means u loves v
    
    // Phase 2: Identify directed Love edges for degree 3 nodes
    for (int i = 1; i <= num_chameleons; ++i) {
        if (adj[i].size() == 3) {
            int x = adj[i][0];
            int y = adj[i][1];
            int z = adj[i][2];
            
            // Logic: The pair {R, S} returns 1. The pairs {L, S} and {L, R} return 2.
            // If query({i, x, y}) == 1, then {x, y} is {R, S}, so z is L(i).
            if (query({i, x, y}) == 1) love[i] = z;
            else if (query({i, x, z}) == 1) love[i] = y;
            else love[i] = x;
        }
    }
    
    vector<int> same(num_chameleons + 1, 0);
    
    // Phase 3: Deduced Same Color edges
    while (true) {
        bool changed = false;
        bool all_done = true;
        
        for (int i = 1; i <= num_chameleons; ++i) {
            if (same[i]) continue;
            all_done = false;
            
            vector<int> candidates;
            for (int v : adj[i]) {
                // Filter out known love edges
                // Edge (i, v) is love if love[i] == v OR love[v] == i
                if (love[i] == v || love[v] == i) continue;
                candidates.push_back(v);
            }
            
            if (candidates.size() == 1) {
                int s = candidates[0];
                same[i] = s;
                same[s] = i;
                changed = true;
            }
        }
        
        if (all_done) break;
        
        // If we are stuck, we have disjoint cycles of mutual loves and same color edges
        // We need to resolve one edge to propagate
        if (!changed) {
            int start = -1;
            for(int i=1; i<=num_chameleons; ++i) if(!same[i]) { start=i; break; }
            if (start == -1) break;
            
            // candidates for start should have size 2 (cycle neighbors)
            vector<int> candidates;
            for (int v : adj[start]) {
                if (love[start] == v || love[v] == start) continue;
                candidates.push_back(v);
            }
            
            int u = start;
            int v = candidates[0];
            
            // Pick a k that is not involved (not u, v, or their neighbors)
            // This k allows distinguishing Same Color (res=2) from Mutual Love (res=3)
            int k = 1;
            while (k == u || k == v || is_nbr(u, k) || is_nbr(v, k)) k++;
            
            int res = query({u, v, k});
            if (res == 2) {
                // {u, v} is Same Color
                same[u] = v;
                same[v] = u;
            } else {
                // {u, v} is Mutual Love
                love[u] = v;
                love[v] = u;
                // The other candidate MUST be Same Color
                int other = candidates[1];
                same[u] = other;
                same[other] = u;
            }
            // Loop will continue and propagate constraints
        }
    }
    
    // Submit answers
    for (int i = 1; i <= num_chameleons; ++i) {
        if (i < same[i]) {
            cout << "Answer " << i << " " << same[i] << endl;
        }
    }
    
    return 0;
}