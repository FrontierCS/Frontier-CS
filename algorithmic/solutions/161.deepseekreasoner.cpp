#include <bits/stdc++.h>
using namespace std;
typedef long long ll;

const ll INF = 1e18;

int N, M, K;
vector<int> x, y;
vector<int> u, v, w;
vector<int> a, b;
vector<vector<ll>> sq_dist;

vector<vector<pair<int, int>>> adj;  // (neighbor, edge_id)
vector<vector<int>> edge_index;      // [N+1][N+1] -> edge_id

vector<vector<ll>> dist_graph;
vector<vector<int>> prev_vertex;

struct DSU {
    vector<int> parent, rank;
    DSU(int n) {
        parent.resize(n);
        rank.assign(n, 0);
        for (int i = 0; i < n; ++i) parent[i] = i;
    }
    int find(int x) {
        if (parent[x] != x) parent[x] = find(parent[x]);
        return parent[x];
    }
    void unite(int x, int y) {
        int rx = find(x), ry = find(y);
        if (rx == ry) return;
        if (rank[rx] < rank[ry]) parent[rx] = ry;
        else if (rank[rx] > rank[ry]) parent[ry] = rx;
        else { parent[ry] = rx; rank[rx]++; }
    }
};

int ceil_sqrt(ll x) {
    if (x <= 0) return 0;
    ll lo = 0, hi = 5000;
    while (lo < hi) {
        ll mid = (lo + hi) / 2;
        if (mid * mid >= x) hi = mid;
        else lo = mid + 1;
    }
    return lo;
}

void dijkstra(int s, vector<ll>& dist, vector<int>& pre) {
    dist.assign(N + 1, INF);
    pre.assign(N + 1, -1);
    vector<bool> visited(N + 1, false);
    dist[s] = 0;
    for (int iter = 0; iter < N; ++iter) {
        int u = -1;
        ll min_d = INF;
        for (int i = 1; i <= N; ++i) {
            if (!visited[i] && dist[i] < min_d) {
                min_d = dist[i];
                u = i;
            }
        }
        if (u == -1) break;
        visited[u] = true;
        for (auto& p : adj[u]) {
            int v = p.first;
            int eid = p.second;
            ll weight = w[eid];
            if (dist[v] > dist[u] + weight) {
                dist[v] = dist[u] + weight;
                pre[v] = u;
            }
        }
    }
}

ll compute_cost(const vector<bool>& active,
                vector<int>* assign_out,
                vector<ll>* max_sq_out,
                vector<int>* on_edges_out) {
    vector<int> act;
    for (int i = 1; i <= N; ++i) if (active[i]) act.push_back(i);
    int nA = act.size();

    // Assignment of residents to closest active vertex
    vector<int> assign(K);
    vector<ll> max_sq(N + 1, 0);
    for (int k = 0; k < K; ++k) {
        ll best = INF;
        int best_i = -1;
        for (int i : act) {
            if (sq_dist[i][k] < best) {
                best = sq_dist[i][k];
                best_i = i;
            }
        }
        assign[k] = best_i;
        if (best > max_sq[best_i]) max_sq[best_i] = best;
    }

    // Covering cost
    ll cover_cost = 0;
    for (int i : act) {
        if (max_sq[i] > 0) {
            int r = ceil_sqrt(max_sq[i]);
            cover_cost += (ll)r * r;
        }
    }

    // Connection cost via MST on active vertices
    ll connection_cost = 0;
    vector<int> on_edges_local(M, 0);
    if (nA > 1) {
        vector<tuple<ll, int, int>> edges;
        for (int i = 0; i < nA; ++i) {
            for (int j = i + 1; j < nA; ++j) {
                int ui = act[i], uj = act[j];
                edges.emplace_back(dist_graph[ui][uj], ui, uj);
            }
        }
        sort(edges.begin(), edges.end());
        DSU dsu(N + 1);
        for (auto& e : edges) {
            ll w_e = get<0>(e);
            int u = get<1>(e), v = get<2>(e);
            if (dsu.find(u) != dsu.find(v)) {
                dsu.unite(u, v);
                // Reconstruct shortest path from u to v
                int cur = v;
                while (cur != u) {
                    int pre = prev_vertex[u][cur];
                    int eid = edge_index[min(pre, cur)][max(pre, cur)];
                    if (on_edges_local[eid] == 0) {
                        on_edges_local[eid] = 1;
                        connection_cost += w[eid];
                    }
                    cur = pre;
                }
            }
        }
    }

    if (assign_out) *assign_out = assign;
    if (max_sq_out) *max_sq_out = max_sq;
    if (on_edges_out) *on_edges_out = on_edges_local;

    return cover_cost + connection_cost;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);

    cin >> N >> M >> K;
    x.resize(N + 1); y.resize(N + 1);
    for (int i = 1; i <= N; ++i) cin >> x[i] >> y[i];
    u.resize(M); v.resize(M); w.resize(M);
    adj.resize(N + 1);
    edge_index.assign(N + 1, vector<int>(N + 1, -1));
    for (int j = 0; j < M; ++j) {
        cin >> u[j] >> v[j] >> w[j];
        adj[u[j]].push_back({v[j], j});
        adj[v[j]].push_back({u[j], j});
        edge_index[min(u[j], v[j])][max(u[j], v[j])] = j;
    }
    a.resize(K); b.resize(K);
    for (int k = 0; k < K; ++k) cin >> a[k] >> b[k];

    // Precompute squared Euclidean distances
    sq_dist.assign(N + 1, vector<ll>(K));
    for (int i = 1; i <= N; ++i) {
        for (int k = 0; k < K; ++k) {
            ll dx = x[i] - a[k];
            ll dy = y[i] - b[k];
            sq_dist[i][k] = dx * dx + dy * dy;
        }
    }

    // All-pairs shortest paths
    dist_graph.assign(N + 1, vector<ll>(N + 1, INF));
    prev_vertex.assign(N + 1, vector<int>(N + 1, -1));
    for (int s = 1; s <= N; ++s) {
        vector<ll> dist;
        vector<int> pre;
        dijkstra(s, dist, pre);
        for (int t = 1; t <= N; ++t) {
            dist_graph[s][t] = dist[t];
            prev_vertex[s][t] = pre[t];
        }
    }

    // Local search
    vector<bool> active(N + 1, false);
    active[1] = true;
    ll best_cost = compute_cost(active, nullptr, nullptr, nullptr);
    bool improved = true;
    while (improved) {
        improved = false;
        // Try adding a vertex
        for (int v = 1; v <= N; ++v) {
            if (active[v]) continue;
            vector<bool> new_active = active;
            new_active[v] = true;
            ll cost = compute_cost(new_active, nullptr, nullptr, nullptr);
            if (cost < best_cost) {
                best_cost = cost;
                active = new_active;
                improved = true;
            }
        }
        // Try removing a vertex (except vertex 1)
        for (int v = 2; v <= N; ++v) {
            if (!active[v]) continue;
            vector<bool> new_active = active;
            new_active[v] = false;
            ll cost = compute_cost(new_active, nullptr, nullptr, nullptr);
            if (cost < best_cost) {
                best_cost = cost;
                active = new_active;
                improved = true;
            }
        }
    }

    // Final solution
    vector<int> assign(K);
    vector<ll> max_sq(N + 1);
    vector<int> on_edges(M, 0);
    compute_cost(active, &assign, &max_sq, &on_edges);

    // Output P_i
    for (int i = 1; i <= N; ++i) {
        if (active[i]) {
            int r = ceil_sqrt(max_sq[i]);
            cout << r;
        } else {
            cout << 0;
        }
        if (i < N) cout << " ";
    }
    cout << "\n";
    // Output B_j
    for (int j = 0; j < M; ++j) {
        cout << on_edges[j];
        if (j < M - 1) cout << " ";
    }
    cout << endl;

    return 0;
}