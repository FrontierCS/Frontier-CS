#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <algorithm>

using namespace std;

// Wrapper function for queries to the interactor
int query(int a, int b, int c) {
    cout << "? " << a << " " << b << " " << c << endl;
    int response;
    cin >> response;
    return response;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n = 100;
    vector<vector<int>> adj(n + 1, vector<int>(n + 1, 0));

    int u = -1, v = -1;
    bool ref_edge_found = false;

    vector<bool> used_for_ref(n + 1, false);

    // Step 1: Find a reference edge (u,v)
    for (int p1 = 1; p1 <= n; ++p1) {
        if (used_for_ref[p1]) continue;
        for (int p2 = p1 + 1; p2 <= n; ++p2) {
            if (used_for_ref[p2]) continue;
            
            used_for_ref[p1] = used_for_ref[p2] = true;

            for (int other = 1; other <= n; ++other) {
                if (other == p1 || other == p2) continue;
                
                int res = query(p1, p2, other);
                if (res == 0) {
                    u = p1;
                    v = p2;
                    adj[u][v] = adj[v][u] = 0;
                    adj[u][other] = adj[other][u] = 0;
                    adj[v][other] = adj[other][v] = 0;
                    ref_edge_found = true;
                    break;
                }
                if (res == 3) {
                    u = p1;
                    v = p2;
                    adj[u][v] = adj[v][u] = 1;
                    adj[u][other] = adj[other][u] = 1;
                    adj[v][other] = adj[other][v] = 1;
                    ref_edge_found = true;
                    break;
                }
            }
            if (ref_edge_found) break;
        }
        if (ref_edge_found) break;
    }
    
    // Collect all vertices other than u and v
    vector<int> others;
    for (int i = 1; i <= n; ++i) {
        if (i != u && i != v) {
            others.push_back(i);
        }
    }

    // Step 2 & 3: Determine edges to u,v and resolve ambiguities
    vector<int> s(n + 1);
    vector<bool> is_resolved(n + 1, false);

    for (int w : others) {
        s[w] = query(u, v, w) - adj[u][v];
        if (s[w] == 0) {
            adj[u][w] = adj[w][u] = 0;
            adj[v][w] = adj[w][v] = 0;
            is_resolved[w] = true;
        } else if (s[w] == 2) {
            adj[u][w] = adj[w][u] = 1;
            adj[v][w] = adj[w][v] = 1;
            is_resolved[w] = true;
        }
    }
    
    int resolved_node = -1;
    for(int w : others) {
        if(is_resolved[w]) {
            resolved_node = w;
            break;
        }
    }
    
    if (resolved_node == -1 && !others.empty()) {
        resolved_node = others[0];
        // Assume edge u-resolved_node is 0. This is safe as it's equivalent
        // to swapping labels of u and v.
        adj[u][resolved_node] = adj[resolved_node][u] = 0;
        adj[v][resolved_node] = adj[resolved_node][v] = 1;
        is_resolved[resolved_node] = true;
    }

    for (int w : others) {
        if (!is_resolved[w]) {
            int q_u = query(u, w, resolved_node);
            int q_v = query(v, w, resolved_node);
            int diff_uv_w = (q_u - q_v) - (adj[u][resolved_node] - adj[v][resolved_node]);
            
            // We have a system of two linear equations:
            // adj[u][w] - adj[v][w] = diff_uv_w
            // adj[u][w] + adj[v][w] = 1
            // Solving this gives:
            adj[u][w] = (1 + diff_uv_w) / 2;
            adj[w][u] = adj[u][w];
            adj[v][w] = 1 - adj[u][w];
            adj[w][v] = adj[v][w];
        }
    }

    // Step 4: Determine remaining edges using u as a pivot
    for (size_t i = 0; i < others.size(); ++i) {
        for (size_t j = i + 1; j < others.size(); ++j) {
            int w1 = others[i];
            int w2 = others[j];
            int res = query(u, w1, w2);
            adj[w1][w2] = adj[w2][w1] = res - adj[u][w1] - adj[u][w2];
        }
    }

    cout << "!" << endl;
    for (int i = 1; i <= n; ++i) {
        string row = "";
        for (int j = 1; j <= n; ++j) {
            row += to_string(adj[i][j]);
        }
        cout << row << endl;
    }

    return 0;
}