#include <iostream>
#include <vector>
#include <bitset>
#include <stack>
#include <algorithm>
#include <cstring>

using namespace std;

const int MAXN = 10000;
const int MAXM = 15000;
const int MAXQ = 70; // number of queries

int N, M;
vector<pair<int, int>> edges;
vector<vector<int>> adj;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);

    cin >> N >> M;
    edges.resize(M);
    adj.resize(N);
    for (int i = 0; i < M; i++) {
        int u, v;
        cin >> u >> v;
        edges[i] = {u, v};
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    // number of queries: use min(70, N) different roots
    int Q = min(MAXQ, N);
    vector<int> roots(Q);
    for (int i = 0; i < Q; i++) roots[i] = i;

    // precompute for each query: orientation and reachability bitsets
    vector<vector<int>> dir(Q, vector<int>(M)); // 0: U->V, 1: V->U
    vector<vector<bitset<MAXN>>> reach(Q, vector<bitset<MAXN>>(N));

    for (int q = 0; q < Q; q++) {
        int root = roots[q];

        // DFS from root to get parent, in-time, out-time
        vector<int> parent(N, -1);
        vector<int> in(N, -1), out(N, -1);
        vector<bool> visited(N, false);
        int timer = 0;
        stack<pair<int, int>> st; // (node, state) state 0=enter, 1=exit
        st.push({root, 0});
        while (!st.empty()) {
            int u = st.top().first;
            int state = st.top().second;
            st.pop();
            if (state == 0) {
                if (visited[u]) continue;
                visited[u] = true;
                in[u] = timer++;
                st.push({u, 1});
                for (int v : adj[u]) {
                    if (!visited[v]) {
                        parent[v] = u;
                        st.push({v, 0});
                    }
                }
            } else {
                out[u] = timer++;
            }
        }

        // Determine orientation for each edge
        for (int i = 0; i < M; i++) {
            int U = edges[i].first, V = edges[i].second;
            int a, b; // orientation from a to b
            if (parent[V] == U) {
                a = U; b = V;
            } else if (parent[U] == V) {
                a = V; b = U;
            } else {
                // back edge: check ancestor
                if (in[U] <= in[V] && in[V] <= out[U]) {
                    a = U; b = V;
                } else {
                    a = V; b = U;
                }
            }
            // set dir such that 0 means U->V, 1 means V->U
            dir[q][i] = (a == U && b == V) ? 0 : 1;
        }

        // Build directed adjacency list for this orientation
        vector<vector<int>> out_adj(N);
        for (int i = 0; i < M; i++) {
            int U = edges[i].first, V = edges[i].second;
            if (dir[q][i] == 0) {
                out_adj[U].push_back(V);
            } else {
                out_adj[V].push_back(U);
            }
        }

        // Compute postorder traversal (DFS from root on directed graph)
        vector<int> order;
        vector<bool> vis(N, false);
        function<void(int)> dfs_post = [&](int u) {
            vis[u] = true;
            for (int v : out_adj[u]) {
                if (!vis[v]) dfs_post(v);
            }
            order.push_back(u);
        };
        dfs_post(root);

        // Compute reachability bitsets
        for (int u = 0; u < N; u++) {
            reach[q][u].reset();
            reach[q][u].set(u);
        }
        for (int u : order) {
            for (int v : out_adj[u]) {
                reach[q][u] |= reach[q][v];
            }
        }
    }

    // Interaction: ask queries
    vector<int> answers(Q);
    for (int q = 0; q < Q; q++) {
        cout << 0;
        for (int i = 0; i < M; i++) {
            cout << " " << dir[q][i];
        }
        cout << endl;
        cout.flush();
        cin >> answers[q];
        if (answers[q] == -1) break; // should not happen
    }

    // Find candidate pair (A, B)
    int candA = -1, candB = -1;
    bitset<MAXN> cand;
    for (int u = 0; u < N; u++) {
        cand.set(); // all bits to 1
        cand.reset(u); // remove u itself
        for (int q = 0; q < Q; q++) {
            if (answers[q] == 1) {
                cand &= reach[q][u];
            } else {
                cand &= (~reach[q][u]);
            }
        }
        if (cand.count() == 1) {
            int v = 0;
            for (; v < N; v++) if (cand[v]) break;
            if (v != u) {
                candA = u;
                candB = v;
                break; // found unique candidate
            }
        }
    }

    // If no candidate found (unlikely), fallback to any pair
    if (candA == -1) {
        candA = 0;
        candB = 1;
    }

    // Output answer
    cout << 1 << " " << candA << " " << candB << endl;
    cout.flush();

    return 0;
}