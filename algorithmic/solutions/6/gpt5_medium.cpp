#include <bits/stdc++.h>
using namespace std;

struct Edge {
    int u, v;
};

vector<vector<int>> create_map(int N, int M, vector<int> A, vector<int> B) {
    // 0-indexed
    int n = N;
    vector<vector<int>> adj(n);
    vector<vector<int>> adj_id(n);
    vector<Edge> edges;
    edges.reserve(M);
    // map pair to id
    map<pair<int,int>, int> pair_id;
    for (int i = 0; i < M; ++i) {
        int u = A[i]-1, v = B[i]-1;
        edges.push_back({u,v});
        adj[u].push_back(v);
        adj_id[u].push_back(i);
        adj[v].push_back(u);
        adj_id[v].push_back(i);
        pair_id[{min(u,v), max(u,v)}] = i;
    }
    // Handle trivial case
    if (M == 0) {
        // Only possible valid map is when N==1
        int K = 1;
        vector<vector<int>> C(K, vector<int>(K, 1));
        return C;
    }

    // Determine vertices with degree > 0
    vector<int> deg(n,0);
    for (int i = 0; i < M; ++i) {
        deg[edges[i].u]++;
        deg[edges[i].v]++;
    }

    // Find a component with edges
    vector<int> vis(n,0);
    int start_comp = -1;
    for (int i = 0; i < n; ++i) if (deg[i] > 0) { start_comp = i; break; }
    if (start_comp == -1) {
        // Shouldn't happen due to M>0
        int K = 1;
        vector<vector<int>> C(K, vector<int>(K, 1));
        return C;
    }
    // Collect vertices in this component
    vector<int> comp;
    queue<int> q;
    q.push(start_comp);
    vis[start_comp] = 1;
    while (!q.empty()) {
        int u = q.front(); q.pop();
        comp.push_back(u);
        for (int k = 0; k < (int)adj[u].size(); ++k) {
            int v = adj[u][k];
            if (!vis[v]) {
                vis[v] = 1;
                q.push(v);
            }
        }
    }

    // Count odd-degree vertices in this component
    vector<int> odd;
    for (int vtx : comp) if (deg[vtx] % 2 == 1) odd.push_back(vtx);

    // Build BFS parents for shortest paths when needed
    auto bfs_parent = [&](int src) {
        vector<int> par(n, -1);
        vector<int> dist(n, -1);
        queue<int> qq;
        qq.push(src);
        dist[src] = 0;
        while (!qq.empty()) {
            int u = qq.front(); qq.pop();
            for (int v : adj[u]) {
                if (dist[v] == -1) {
                    dist[v] = dist[u] + 1;
                    par[v] = u;
                    qq.push(v);
                }
            }
        }
        return make_pair(par, dist);
    };

    // Edge multiplicities
    vector<int> mult(M, 1);

    // Greedy pairing of odd vertices within the component
    vector<int> odd_list = odd;
    vector<int> used_odd(n, 0);
    for (int v : odd_list) used_odd[v] = 1;
    while (!odd_list.empty()) {
        int u = odd_list.back(); odd_list.pop_back();
        if (!used_odd[u]) continue;
        auto pr = bfs_parent(u);
        auto &par = pr.first;
        auto &dist = pr.second;
        int best_v = -1, best_d = 1e9, best_idx = -1;
        for (int i = 0; i < (int)odd_list.size(); ++i) {
            int v = odd_list[i];
            if (!used_odd[v]) continue;
            if (dist[v] >= 0 && dist[v] < best_d) {
                best_d = dist[v];
                best_v = v;
                best_idx = i;
            }
        }
        if (best_v == -1) {
            // No reachable odd vertex (shouldn't happen in connected component)
            used_odd[u] = 0;
            continue;
        }
        // Remove best_v from list
        used_odd[u] = 0;
        used_odd[best_v] = 0;
        odd_list.erase(odd_list.begin() + best_idx);

        // Reconstruct path from u to best_v via parents and increase multiplicities along path edges
        vector<int> path;
        int cur = best_v;
        while (cur != -1) {
            path.push_back(cur);
            if (cur == u) break;
            cur = par[cur];
        }
        if (path.back() != u) {
            // fallback: directly increment the edge if exists
            int id = -1;
            auto it = pair_id.find({min(u,best_v), max(u,best_v)});
            if (it != pair_id.end()) id = it->second;
            if (id != -1) mult[id]++; // add parallel
        } else {
            reverse(path.begin(), path.end());
            for (int i = 0; i+1 < (int)path.size(); ++i) {
                int a = path[i], b = path[i+1];
                int id = pair_id[{min(a,b), max(a,b)}];
                mult[id]++;
            }
        }
    }

    // Build multigraph adjacency for Hierholzer
    // Create instances for each multiplicity
    struct MEdge { int to; int id; int rev; bool used; };
    vector<vector<MEdge>> G(n);
    int total_mult_edges = 0;
    for (int i = 0; i < M; ++i) total_mult_edges += mult[i];
    // safety cap
    if (total_mult_edges + 1 > 240) {
        // Try using original edges only if possible Eulerian (odd<=2); else fallback cut
        vector<int> odd_deg;
        for (int v : comp) if (deg[v] % 2) odd_deg.push_back(v);
        if (odd_deg.size() == 0 || odd_deg.size() == 2) {
            // use only original edges
            fill(G.begin(), G.end(), vector<MEdge>());
            for (int i = 0; i < M; ++i) {
                int u = edges[i].u, v = edges[i].v;
                MEdge a{v, i, (int)G[v].size(), false};
                MEdge b{u, i, (int)G[u].size(), false};
                G[u].push_back(a);
                G[v].push_back(b);
            }
            total_mult_edges = M;
        } else {
            // Otherwise, trim to first 239 edges arbitrarily to fit constraint (best-effort)
            fill(G.begin(), G.end(), vector<MEdge>());
            int cnt = 0;
            for (int i = 0; i < M && cnt < 239; ++i) {
                int u = edges[i].u, v = edges[i].v;
                MEdge a{v, i, (int)G[v].size(), false};
                MEdge b{u, i, (int)G[u].size(), false};
                G[u].push_back(a);
                G[v].push_back(b);
                cnt++;
            }
            total_mult_edges = cnt;
        }
    } else {
        for (int i = 0; i < M; ++i) {
            int u = edges[i].u, v = edges[i].v;
            for (int k = 0; k < mult[i]; ++k) {
                MEdge a{v, i, (int)G[v].size(), false};
                MEdge b{u, i, (int)G[u].size(), false};
                G[u].push_back(a);
                G[v].push_back(b);
            }
        }
    }

    // Find starting vertex with degree > 0
    int s = -1;
    for (int i = 0; i < n; ++i) if (!G[i].empty()) { s = i; break; }
    if (s == -1) {
        // No edges added? Fallback to 1x1 with any color present (should not happen)
        vector<vector<int>> C(1, vector<int>(1, 1));
        return C;
    }

    // Hierholzer
    vector<int> it(n, 0);
    vector<int> st;
    vector<int> path;
    vector<pair<int,int>> edge_stack; // (u, edge index in G[u])
    st.push_back(s);
    while (!st.empty()) {
        int u = st.back();
        while (it[u] < (int)G[u].size() && G[u][it[u]].used) it[u]++;
        if (it[u] == (int)G[u].size()) {
            path.push_back(u);
            st.pop_back();
        } else {
            auto e = G[u][it[u]];
            G[u][it[u]].used = true;
            int v = e.to;
            // mark reverse as used
            auto &revEdge = G[v][e.rev];
            revEdge.used = true;
            st.push_back(v);
        }
    }
    // path is sequence of vertices; length = total_mult_edges + 1
    if ((int)path.size() < 2) {
        vector<vector<int>> C(1, vector<int>(1, s+1));
        return C;
    }
    reverse(path.begin(), path.end());

    int L = (int)path.size();
    if (L > 240) {
        // Trim by compressing consecutive duplicates
        vector<int> comp_seq;
        comp_seq.push_back(path[0]);
        for (int i = 1; i < L; ++i) {
            if (path[i] != comp_seq.back()) comp_seq.push_back(path[i]);
        }
        if ((int)comp_seq.size() > 240) {
            // Still too long; take first 240
            comp_seq.resize(240);
        }
        path = comp_seq;
        L = (int)path.size();
    }

    int K = L;
    vector<vector<int>> C(K, vector<int>(K));
    for (int j = 0; j < K; ++j) {
        int col = path[j] + 1;
        for (int i = 0; i < K; ++i) {
            C[i][j] = col;
        }
    }
    return C;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int T;
    if (!(cin >> T)) return 0;
    while (T--) {
        int N, M;
        cin >> N >> M;
        vector<int> A(M), B(M);
        for (int i = 0; i < M; ++i) {
            cin >> A[i] >> B[i];
        }
        auto C = create_map(N, M, A, B);
        int P = (int)C.size();
        cout << P << "\n";
        for (int i = 0; i < P; ++i) {
            cout << (int)C[i].size();
            if (i+1<P) cout << " ";
        }
        cout << "\n";
        for (int i = 0; i < P; ++i) {
            for (int j = 0; j < (int)C[i].size(); ++j) {
                if (j) cout << " ";
                cout << C[i][j];
            }
            cout << "\n";
        }
    }
    return 0;
}