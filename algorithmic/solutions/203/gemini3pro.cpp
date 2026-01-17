#include <iostream>
#include <vector>
#include <algorithm>

using namespace std;

// Global variables
int N;
vector<int> adj[1005];         // Adjacency list for the connection graph
int love_target[1005];         // Stores L(u) if identified (for degree 3 nodes)
bool used_ans[1005];           // Tracks if a chameleon has been paired in the answer

// Perform a query with a list of chameleons
int query(const vector<int>& v) {
    if (v.empty()) return 0;
    cout << "Query " << v.size();
    for (int x : v) cout << " " << x;
    cout << endl;
    int res;
    cin >> res;
    return res;
}

// Check if chameleon u has any connection (edge) with any chameleon in set s
bool check(int u, const vector<int>& s) {
    if (s.empty()) return false;
    vector<int> req = s;
    req.push_back(u);
    int res = query(req);
    // If result is not |S| + 1, there is at least one edge reducing the color count
    return res != (int)s.size() + 1;
}

// Recursively find neighbors of u within set s
void find_edges(int u, const vector<int>& s) {
    if (s.empty()) return;
    
    // Optimization: A node has at most 3 neighbors in the connection graph.
    // If we already found 3, we don't need to search further.
    if (adj[u].size() >= 3) return;
    
    // If no edge exists between u and s, skip this branch
    if (!check(u, s)) return;
    
    // Base case: s has size 1, so s[0] is a neighbor
    if (s.size() == 1) {
        adj[u].push_back(s[0]);
        adj[s[0]].push_back(u);
        return;
    }
    
    // Divide and conquer
    int mid = s.size() / 2;
    vector<int> l(s.begin(), s.begin() + mid);
    vector<int> r(s.begin() + mid, s.end());
    
    find_edges(u, l);
    find_edges(u, r);
}

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    
    if (!(cin >> N)) return 0;
    
    // Maintain a list of independent sets to minimize queries
    // The graph has max degree 3, so it is 4-colorable (or close to it greedily)
    vector<vector<int>> independent_sets;
    
    // Phase 1: Construct the graph
    for (int i = 1; i <= 2 * N; ++i) {
        // Find neighbors of i among already processed vertices (1 to i-1)
        // We search within each independent set
        for (const auto& s : independent_sets) {
            find_edges(i, s);
        }
        
        // Add i to the first independent set where it has no conflicts
        bool placed = false;
        for (auto& s : independent_sets) {
            bool conflict = false;
            // Check adjacency: if i is connected to any node in s, we can't put i in s
            for (int neighbor : adj[i]) {
                for (int member : s) {
                    if (member == neighbor) {
                        conflict = true;
                        break;
                    }
                }
                if (conflict) break;
            }
            if (!conflict) {
                s.push_back(i);
                placed = true;
                break;
            }
        }
        // If i fits in no existing set, create a new one
        if (!placed) {
            independent_sets.push_back({i});
        }
    }
    
    // Phase 2: Identify Love edges
    // Nodes with degree 3 have neighbors {c_u, L(u), L^-1(u)}.
    // Nodes with degree 1 have neighbor {c_u}.
    for (int i = 1; i <= 2 * N; ++i) {
        if (adj[i].size() == 3) {
            int x = adj[i][0];
            int y = adj[i][1];
            int z = adj[i][2];
            
            // Property: Query({i, L^-1(i), c_i}) returns 1.
            // This means the pair from neighbors that yields 1 with i contains L^-1(i) and c_i.
            // The remaining neighbor must be L(i).
            
            if (query({i, x, y}) == 1) {
                love_target[i] = z; // z is left out
            } else if (query({i, x, z}) == 1) {
                love_target[i] = y; // y is left out
            } else {
                love_target[i] = x; // x is left out
            }
        }
    }
    
    // Phase 3: Output answers
    for (int i = 1; i <= 2 * N; ++i) {
        if (used_ans[i]) continue;
        
        // For each node, the color partner is the neighbor that is NOT connected via a Love edge.
        // An edge {i, v} is a Love edge if L(i) == v or L(v) == i.
        // Otherwise, it is a Color edge.
        
        for (int v : adj[i]) {
            if (love_target[i] != v && love_target[v] != i) {
                cout << "Answer " << i << " " << v << endl;
                used_ans[i] = true;
                used_ans[v] = true;
                break;
            }
        }
    }
    
    return 0;
}