#include <iostream>
#include <vector>
#include <algorithm>
#include <stack>
#include <utility>

using namespace std;

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M;
    cin >> N >> M;

    vector<vector<int>> adj(N);
    vector<pair<int, int>> edges(M);
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        edges[i] = {u, v};
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    // sort adjacency lists for deterministic DFS
    for (int i = 0; i < N; ++i) {
        sort(adj[i].begin(), adj[i].end());
    }

    const int K = min(30, N); // number of queries (roots)
    vector<vector<int>> entry(K, vector<int>(N));
    vector<vector<int>> exit(K, vector<int>(N));
    vector<vector<int>> dir(K, vector<int>(M));

    // Precompute DFS trees for each root
    for (int idx = 0; idx < K; ++idx) {
        int r = idx; // root is the node with index idx
        int timer = 0;
        stack<pair<int, bool>> st;
        vector<bool> vis(N, false);
        st.push({r, false});
        vis[r] = true;
        while (!st.empty()) {
            auto [u, isExit] = st.top();
            st.pop();
            if (!isExit) {
                entry[idx][u] = timer++;
                st.push({u, true});
                // push children in reverse order to visit in sorted order
                for (auto it = adj[u].rbegin(); it != adj[u].rend(); ++it) {
                    int v = *it;
                    if (!vis[v]) {
                        vis[v] = true;
                        st.push({v, false});
                    }
                }
            } else {
                exit[idx][u] = timer++;
            }
        }

        // Determine orientation for each edge based on ancestor relationship
        for (int i = 0; i < M; ++i) {
            int u = edges[i].first, v = edges[i].second;
            if (entry[idx][u] <= entry[idx][v] && exit[idx][u] >= exit[idx][v]) {
                // u is ancestor of v
                dir[idx][i] = 0; // orient from u to v
            } else {
                // v must be ancestor of u (since graph is undirected and DFS tree)
                dir[idx][i] = 1; // orient from v to u
            }
        }
    }

    vector<int> ans(K);
    // Ask queries
    for (int idx = 0; idx < K; ++idx) {
        cout << 0;
        for (int i = 0; i < M; ++i) {
            cout << ' ' << dir[idx][i];
        }
        cout << endl;
        cout.flush();
        cin >> ans[idx];
    }

    // Decode: find the unique pair (A,B) that matches all answers
    for (int b = 0; b < N; ++b) {
        for (int a = 0; a < N; ++a) {
            if (a == b) continue;
            bool ok = true;
            for (int idx = 0; idx < K; ++idx) {
                bool is_ancestor = (entry[idx][a] <= entry[idx][b] && exit[idx][a] >= exit[idx][b]);
                if (is_ancestor != ans[idx]) {
                    ok = false;
                    break;
                }
            }
            if (ok) {
                cout << 1 << ' ' << a << ' ' << b << endl;
                cout.flush();
                return 0;
            }
        }
    }

    // Should never reach here
    return 0;
}