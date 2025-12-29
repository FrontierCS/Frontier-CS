#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <bitset>
#include <string>

using namespace std;

int n;
bitset<2005> adj[2005]; 
int p[2005];
bool used[2005];
bool found_sol = false;
vector<int> best_p;

// BFS to check connectivity of unused vertices + target in specific color
bool is_connected(int u, int target, const bitset<2005>& unused, int color) {
    bitset<2005> visited;
    bitset<2005> current_level;
    current_level[u] = 1;
    visited[u] = 1;
    
    // The set of nodes we care about is unused | {target} | {u}
    bitset<2005> scope = unused;
    scope[target] = 1;
    scope[u] = 1; 
    
    int total_nodes = scope.count();
    
    bitset<2005> q = current_level;
    while (q.any()) {
        bitset<2005> next_q;
        for (int v = q._Find_first(); v < 2005; v = q._Find_next(v)) {
            // Check boundary
            if (v > n) break; 
            if (color == 1) {
                next_q |= (adj[v] & scope);
            } else {
                next_q |= (~adj[v] & scope);
            }
        }
        next_q &= ~visited;
        if (next_q.none()) break;
        visited |= next_q;
        q = next_q;
    }
    
    return (visited & scope).count() == total_nodes;
}

// Check if every unused node has at least one edge of 'color' to another unused node or u or target
bool check_degrees(int u, int target, const bitset<2005>& unused, int color) {
    // Check current node u connectivity
    if (color == 1) {
        if ((adj[u] & unused).none() && !adj[u][target]) return false;
    } else {
        if ((~adj[u] & unused).none() && !(!adj[u][target])) return false;
    }
    
    // Check all unused nodes
    for (int v = unused._Find_first(); v < 2005; v = unused._Find_next(v)) {
         if (v > n) break;
         if (color == 1) {
             bool has_edge = false;
             if (adj[v][target]) has_edge = true;
             else if (adj[v][u]) has_edge = true;
             else if ((adj[v] & unused).any()) has_edge = true; // rough check
             
             // More precise:
             // bitset<2005> neighbors = adj[v] & unused;
             // if (neighbors.any()) has_edge = true;
             
             if (!has_edge) return false;
         } else {
             bool has_edge = false;
             if (!adj[v][target]) has_edge = true;
             else if (!adj[v][u]) has_edge = true;
             else if ((~adj[v] & unused).any()) has_edge = true;
             
             if (!has_edge) return false;
         }
    }
    return true;
}

void dfs(int idx, int phase, int pattern_type, bitset<2005>& unused_mask) {
    if (found_sol) return;
    
    int u = p[idx-1];
    
    if (idx == n + 1) {
        int c = adj[u][p[1]]; 
        bool ok = false;
        if (pattern_type == 0) { // 0 -> 1
            if (phase == 0) ok = true; 
            else if (c == 1) ok = true;
        } else { // 1 -> 0
            if (phase == 0) ok = true;
            else if (c == 0) ok = true;
        }
        
        if (ok) {
            best_p.assign(p + 1, p + n + 1);
            found_sol = true;
        }
        return;
    }

    if (phase == 1) {
        int color = (pattern_type == 0) ? 1 : 0;
        if (!check_degrees(u, p[1], unused_mask, color)) return;
        if (!is_connected(u, p[1], unused_mask, color)) return;
    }

    for (int v = 1; v <= n; ++v) {
        if (!used[v]) {
            int c = adj[u][v];
            int next_phase = phase;
            bool possible = true;
            
            if (pattern_type == 0) { // 0->1
                if (phase == 0) {
                    if (c == 1) next_phase = 1;
                } else {
                    if (c == 0) possible = false;
                }
            } else { // 1->0
                if (phase == 0) { 
                    if (c == 0) next_phase = 1;
                } else {
                    if (c == 1) possible = false;
                }
            }
            
            if (possible) {
                p[idx] = v;
                used[v] = 1;
                unused_mask[v] = 0;
                
                dfs(idx + 1, next_phase, pattern_type, unused_mask);
                if (found_sol) return;
                
                unused_mask[v] = 1;
                used[v] = 0;
            }
        }
    }
}

void solve() {
    for (int i = 1; i <= n; ++i) {
        string s; cin >> s;
        adj[i].reset();
        for (int j = 1; j <= n; ++j) {
            if (s[j-1] == '1') adj[i][j] = 1;
        }
    }

    found_sol = false;
    best_p.clear();
    
    vector<int> sol1, sol2;
    
    p[1] = 1; used[1] = 1;
    bitset<2005> mask;
    for(int i=2; i<=n; ++i) mask[i] = 1;
    
    dfs(2, 0, 0, mask); // Pattern 0->1
    if (found_sol) sol1 = best_p;
    
    found_sol = false;
    for(int i=1; i<=n; ++i) used[i] = 0;
    best_p.clear();
    
    p[1] = 1; used[1] = 1;
    mask.reset();
    for(int i=2; i<=n; ++i) mask[i] = 1;
    
    dfs(2, 0, 1, mask); // Pattern 1->0
    if (found_sol) sol2 = best_p;
    
    if (sol1.empty() && sol2.empty()) {
        cout << -1 << endl;
    } else if (sol1.empty()) {
        for(int i=0; i<n; ++i) cout << sol2[i] << (i==n-1?"":" ");
        cout << endl;
    } else if (sol2.empty()) {
        for(int i=0; i<n; ++i) cout << sol1[i] << (i==n-1?"":" ");
        cout << endl;
    } else {
        if (sol1 < sol2) {
            for(int i=0; i<n; ++i) cout << sol1[i] << (i==n-1?"":" ");
            cout << endl;
        } else {
            for(int i=0; i<n; ++i) cout << sol2[i] << (i==n-1?"":" ");
            cout << endl;
        }
    }
    
    for(int i=1; i<=n; ++i) used[i] = 0;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    while(cin >> n) {
        solve();
    }
    return 0;
}