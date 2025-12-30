#include <iostream>
#include <vector>
#include <algorithm>
#include <utility>

using namespace std;

// Global constants
const int MAXN = 100005;
const int LOGN = 18; 

// Global data structures
int n;
long long D[MAXN]; 
int parent_node[MAXN];
vector<int> adj[MAXN];
int sz[MAXN];
int rep[MAXN];
int up[MAXN][LOGN];

// Interaction
long long query(int u, int v) {
    cout << "? " << u << " " << v << endl;
    long long d;
    cin >> d;
    return d;
}

// Add u as child of p
void add_node(int u, int p) {
    parent_node[u] = p;
    adj[p].push_back(u);
    sz[u] = 1;
    rep[u] = u;
    
    // Binary lifting update
    up[u][0] = p;
    for (int k = 1; k < LOGN; ++k) {
        up[u][k] = up[up[u][k-1]][k-1];
    }
    
    // Update size and representative leaf up to root
    int curr = p;
    while (curr != 0) {
        sz[curr]++;
        rep[curr] = u; // u is the deepest node in this subtree now
        curr = parent_node[curr];
    }
}

// Find ancestor of u with specific distance from root
int get_ancestor_by_dist(int u, long long target_dist) {
    if (D[u] == target_dist) return u;
    for (int k = LOGN - 1; k >= 0; --k) {
        int anc = up[u][k];
        if (anc != 0 && D[anc] >= target_dist) {
            u = anc;
        }
    }
    return u;
}

void solve() {
    if (!(cin >> n)) return;
    
    // Clean up for this test case
    for (int i = 1; i <= n; ++i) {
        adj[i].clear();
        sz[i] = 0;
        rep[i] = 0;
        for (int k = 0; k < LOGN; ++k) up[i][k] = 0;
    }

    if (n == 1) {
        cout << "! " << endl;
        return;
    }

    D[1] = 0;
    vector<pair<long long, int>> nodes;
    // Query distances from root
    for (int i = 2; i <= n; ++i) {
        D[i] = query(1, i);
        nodes.push_back({D[i], i});
    }

    // Sort by distance
    sort(nodes.begin(), nodes.end());

    // Initialize root
    sz[1] = 1;
    rep[1] = 1;
    
    for (auto& p : nodes) {
        int u = p.second;
        long long d_u = p.first;
        
        int curr = 1;
        
        // Traverse down to find parent
        while (true) {
            if (adj[curr].empty()) {
                add_node(u, curr);
                break;
            }
            
            // Sort children by subtree size descending to use HLD heuristic
            sort(adj[curr].begin(), adj[curr].end(), [](int a, int b) {
                return sz[a] > sz[b];
            });
            
            bool found = false;
            for (int child : adj[curr]) {
                int l = rep[child];
                long long dist_ul = query(u, l);
                long long dist_lca = (d_u + D[l] - dist_ul) / 2;
                
                if (dist_lca == D[curr]) {
                    // LCA is curr, so u is not in this child's branch
                    continue;
                } else {
                    // LCA is in this child's branch
                    int w = get_ancestor_by_dist(l, dist_lca);
                    curr = w;
                    found = true;
                    break;
                }
            }
            
            if (!found) {
                // Not in any child's subtree -> direct child of curr
                add_node(u, curr);
                break;
            }
        }
    }

    cout << "!";
    for (int i = 2; i <= n; ++i) {
        int p = parent_node[i];
        long long w = D[i] - D[p];
        cout << " " << p << " " << i << " " << w;
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