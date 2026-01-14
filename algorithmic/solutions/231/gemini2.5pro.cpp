#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <set>

using namespace std;

const int MAXN = 1005;
const int MAX_G = 2010;
vector<int> adj[MAXN];
int n, m, T;

vector<pair<int, int>> added_edges;

int g[MAXN];
int v_of_g[MAX_G];

vector<int> sorted_nodes;
bool visited[MAXN];

void topo_dfs(int u) {
    visited[u] = true;
    for (int v : adj[u]) {
        if (!visited[v]) {
            topo_dfs(v);
        }
    }
    sorted_nodes.push_back(u);
}

void calculate_grundy() {
    for (int i = 1; i <= n; ++i) g[i] = -1;
    for (int i = 0; i < MAX_G; ++i) v_of_g[i] = 0;

    bool g_val_used[MAX_G] = {false};
    bool seen_g[MAX_G];

    for (int u : sorted_nodes) {
        fill(seen_g, seen_g + n + 1, false);
        for (int v : adj[u]) {
            if(g[v] <= n) seen_g[g[v]] = true;
        }

        int current_g = 0;
        while (seen_g[current_g]) {
            current_g++;
        }

        while (g_val_used[current_g]) {
            int v_to_connect = v_of_g[current_g];
            bool edge_exists = false;
            for (int neighbor : adj[u]) {
                if (neighbor == v_to_connect) {
                    edge_exists = true;
                    break;
                }
            }
            if (!edge_exists) {
                adj[u].push_back(v_to_connect);
                added_edges.push_back({u, v_to_connect});
            }
            
            seen_g[current_g] = true;
            while (seen_g[current_g]) {
                current_g++;
            }
        }
        g[u] = current_g;
        g_val_used[current_g] = true;
        v_of_g[current_g] = u;
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> n >> m >> T;

    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
    }

    // Phase 1: Graph modification
    for (int i = 1; i <= n; ++i) {
        if (!visited[i]) {
            topo_dfs(i);
        }
    }
    // sorted_nodes is already in reverse topological order

    calculate_grundy();
    
    cout << added_edges.size() << endl;
    for (const auto& edge : added_edges) {
        cout << "+ " << edge.first << " " << edge.second << endl;
    }
    cout.flush();

    // Precompute query sets and their nim-sums
    int B = 0;
    while ((1 << B) <= n) {
        B++;
    }
    
    vector<vector<int>> query_sets(B);
    vector<int> query_nim_sums(B, 0);
    vector<int> final_g_to_v(n);

    for(int i = 1; i <= n; ++i) {
        if (g[i] < n) {
           final_g_to_v[g[i]] = i;
        }
    }

    for (int b = 0; b < B; ++b) {
        for (int i = 0; i < n; ++i) {
            if ((i >> b) & 1) {
                query_sets[b].push_back(final_g_to_v[i]);
                query_nim_sums[b] ^= i;
            }
        }
    }

    // Phase 2: T rounds
    for (int t = 0; t < T; ++t) {
        vector<bool> response_bits(B);
        for (int b = 0; b < B; ++b) {
            cout << "? " << query_sets[b].size();
            for (int node : query_sets[b]) {
                cout << " " << node;
            }
            cout << endl;
            cout.flush();

            string response;
            cin >> response;
            if (response == "Lose") {
                response_bits[b] = true;
            } else {
                response_bits[b] = false;
            }
        }

        vector<int> candidates;
        for (int i = 1; i <= n; ++i) {
            bool consistent = true;
            for (int b = 0; b < B; ++b) {
                bool should_be_lose = (g[i] == query_nim_sums[b]);
                if (should_be_lose != response_bits[b]) {
                    consistent = false;
                    break;
                }
            }
            if (consistent) {
                candidates.push_back(i);
            }
        }

        cout << "! " << candidates[0] << endl;
        cout.flush();

        string result;
        cin >> result;
        if (result == "Wrong") {
            return 0;
        }
    }

    return 0;
}