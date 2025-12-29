#include <bits/stdc++.h>
using namespace std;

typedef long long ll;

const double INF_double = 1e18;
const ll INF_ll = 1e18;

int N, M, K;
vector<int> x, y;
vector<int> u, v, w;
vector<int> a, b;

vector<vector<double>> d_vertex_resident;
vector<vector<ll>> dist_graph;
vector<vector<int>> pred;
map<pair<int,int>, pair<int,ll>> edge_map;

vector<int> S_list;
vector<int> idx_in_S;
vector<int> assigned;
vector<double> radius;
vector<bool> edge_in_T;
ll total_edge_weight;
ll total_rad_cost;

int get_P(double r) {
    if (r <= 0) return 0;
    int p = (int)r;
    if (p < r - 1e-9) p++;
    if (p > 5000) p = 5000;
    return p;
}

ll rad_cost(double r) {
    int p = get_P(r);
    return (ll)p * p;
}

vector<int> get_path_edges(int a, int b) {
    vector<int> edges;
    int cur = b;
    while (cur != a) {
        int prev = pred[a][cur];
        int u = cur, v = prev;
        if (u > v) swap(u, v);
        auto it = edge_map.find({u, v});
        if (it == edge_map.end()) {
            cerr << "Error: edge not found in map" << endl;
            exit(1);
        }
        edges.push_back(it->second.first);
        cur = prev;
    }
    return edges;
}

int main() {
    cin >> N >> M >> K;
    x.resize(N); y.resize(N);
    for (int i = 0; i < N; i++) cin >> x[i] >> y[i];
    u.resize(M); v.resize(M); w.resize(M);
    for (int j = 0; j < M; j++) {
        cin >> u[j] >> v[j] >> w[j];
        u[j]--; v[j]--;
        if (u[j] > v[j]) swap(u[j], v[j]);
        edge_map[{u[j], v[j]}] = {j, w[j]};
    }
    a.resize(K); b.resize(K);
    for (int k = 0; k < K; k++) cin >> a[k] >> b[k];

    d_vertex_resident.assign(N, vector<double>(K));
    for (int i = 0; i < N; i++) {
        for (int k = 0; k < K; k++) {
            double dx = x[i] - a[k];
            double dy = y[i] - b[k];
            d_vertex_resident[i][k] = sqrt(dx*dx + dy*dy);
        }
    }

    vector<vector<pair<int,ll>>> adj(N);
    for (int j = 0; j < M; j++) {
        adj[u[j]].push_back({v[j], w[j]});
        adj[v[j]].push_back({u[j], w[j]});
    }

    dist_graph.assign(N, vector<ll>(N, INF_ll));
    pred.assign(N, vector<int>(N, -1));
    for (int s = 0; s < N; s++) {
        dist_graph[s][s] = 0;
        priority_queue<pair<ll,int>, vector<pair<ll,int>>, greater<pair<ll,int>>> pq;
        pq.push({0, s});
        while (!pq.empty()) {
            auto [d, u] = pq.top(); pq.pop();
            if (d > dist_graph[s][u]) continue;
            for (auto& [v, weight] : adj[u]) {
                ll nd = d + weight;
                if (nd < dist_graph[s][v]) {
                    dist_graph[s][v] = nd;
                    pred[s][v] = u;
                    pq.push({nd, v});
                }
            }
        }
    }

    idx_in_S.assign(N, -1);
    S_list.push_back(0);
    idx_in_S[0] = 0;
    assigned.resize(K, 0);
    double r0 = 0;
    for (int k = 0; k < K; k++) r0 = max(r0, d_vertex_resident[0][k]);
    radius.push_back(r0);
    total_rad_cost = rad_cost(r0);
    edge_in_T.assign(M, false);
    total_edge_weight = 0;
    ll current_cost = total_rad_cost + total_edge_weight;

    int max_additions = 30;
    int add_count = 0;
    while (add_count < max_additions) {
        add_count++;
        int best_i = -1;
        double best_new_rad_i = 0;
        vector<double> best_new_rad_for_S;
        vector<int> best_path_edges;
        ll best_delta = 0;

        for (int i = 0; i < N; i++) {
            if (idx_in_S[i] != -1) continue;
            vector<double> new_rad(S_list.size(), 0.0);
            double new_rad_i = 0.0;
            for (int k = 0; k < K; k++) {
                int cur_j = assigned[k];
                double d_cur = d_vertex_resident[cur_j][k];
                double d_i = d_vertex_resident[i][k];
                if (d_i < d_cur) new_rad_i = max(new_rad_i, d_i);
                else new_rad[idx_in_S[cur_j]] = max(new_rad[idx_in_S[cur_j]], d_cur);
            }
            ll old_rad_sum = 0;
            for (double r : radius) old_rad_sum += rad_cost(r);
            ll new_rad_sum = rad_cost(new_rad_i);
            for (double r : new_rad) new_rad_sum += rad_cost(r);
            ll delta_rad = new_rad_sum - old_rad_sum;

            int best_s = -1;
            ll min_dist = INF_ll;
            for (int s : S_list) {
                if (dist_graph[i][s] < min_dist) {
                    min_dist = dist_graph[i][s];
                    best_s = s;
                }
            }
            if (best_s == -1) continue;

            vector<int> path_edges = get_path_edges(best_s, i);
            ll delta_edge = 0;
            for (int e_idx : path_edges) {
                if (!edge_in_T[e_idx]) delta_edge += w[e_idx];
            }
            ll delta = delta_rad + delta_edge;
            if (best_i == -1 || delta < best_delta) {
                best_delta = delta;
                best_i = i;
                best_new_rad_i = new_rad_i;
                best_new_rad_for_S = new_rad;
                best_path_edges = path_edges;
            }
        }

        if (best_i == -1 || best_delta >= 0) break;

        idx_in_S[best_i] = S_list.size();
        S_list.push_back(best_i);
        for (size_t pos = 0; pos < best_new_rad_for_S.size(); pos++)
            radius[pos] = best_new_rad_for_S[pos];
        radius.push_back(best_new_rad_i);
        for (int k = 0; k < K; k++) {
            if (d_vertex_resident[best_i][k] < d_vertex_resident[assigned[k]][k])
                assigned[k] = best_i;
        }
        for (int e_idx : best_path_edges) {
            if (!edge_in_T[e_idx]) {
                edge_in_T[e_idx] = true;
                total_edge_weight += w[e_idx];
            }
        }
        total_rad_cost = 0;
        for (double r : radius) total_rad_cost += rad_cost(r);
        current_cost = total_rad_cost + total_edge_weight;
    }

    vector<set<int>> T_adj(N);
    for (int j = 0; j < M; j++) {
        if (edge_in_T[j]) {
            T_adj[u[j]].insert(v[j]);
            T_adj[v[j]].insert(u[j]);
        }
    }

    bool removed;
    do {
        removed = false;
        T_adj.assign(N, set<int>());
        for (int j = 0; j < M; j++) {
            if (edge_in_T[j]) {
                T_adj[u[j]].insert(v[j]);
                T_adj[v[j]].insert(u[j]);
            }
        }

        for (size_t idx = 0; idx < S_list.size(); idx++) {
            int i = S_list[idx];
            if (i == 0) continue;
            if (T_adj[i].size() == 1) {
                int neighbor = *T_adj[i].begin();
                int ui = i, vi = neighbor;
                if (ui > vi) swap(ui, vi);
                auto it = edge_map.find({ui, vi});
                if (it == edge_map.end()) continue;
                int e_idx = it->second.first;
                ll edge_weight = it->second.second;

                vector<double> cur_rad_for_vertex(N, 0.0);
                for (size_t pos = 0; pos < S_list.size(); pos++)
                    cur_rad_for_vertex[S_list[pos]] = radius[pos];
                vector<double> new_max_for_vertex(N, 0.0);
                for (int j : S_list)
                    if (j != i) new_max_for_vertex[j] = cur_rad_for_vertex[j];

                for (int k = 0; k < K; k++) {
                    if (assigned[k] == i) {
                        double min_d = INF_double;
                        int best_j = -1;
                        for (int j : S_list) {
                            if (j == i) continue;
                            double d = d_vertex_resident[j][k];
                            if (d < min_d) { min_d = d; best_j = j; }
                        }
                        if (best_j != -1)
                            new_max_for_vertex[best_j] = max(new_max_for_vertex[best_j], min_d);
                    }
                }

                ll new_rad_cost = 0;
                for (int j : S_list)
                    if (j != i) new_rad_cost += rad_cost(new_max_for_vertex[j]);
                ll new_edge_weight = total_edge_weight - edge_weight;
                ll new_cost = new_rad_cost + new_edge_weight;
                if (new_cost < current_cost) {
                    removed = true;
                    S_list.erase(S_list.begin() + idx);
                    idx_in_S.assign(N, -1);
                    for (size_t pos = 0; pos < S_list.size(); pos++)
                        idx_in_S[S_list[pos]] = pos;
                    for (int k = 0; k < K; k++) {
                        if (assigned[k] == i) {
                            double min_d = INF_double;
                            int best_j = -1;
                            for (int j : S_list) {
                                double d = d_vertex_resident[j][k];
                                if (d < min_d) { min_d = d; best_j = j; }
                            }
                            assigned[k] = best_j;
                        }
                    }
                    radius.clear();
                    for (int j : S_list) radius.push_back(new_max_for_vertex[j]);
                    edge_in_T[e_idx] = false;
                    total_edge_weight = new_edge_weight;
                    total_rad_cost = new_rad_cost;
                    current_cost = new_cost;
                    break;
                }
            }
        }
    } while (removed);

    T_adj.assign(N, set<int>());
    for (int j = 0; j < M; j++) {
        if (edge_in_T[j]) {
            T_adj[u[j]].insert(v[j]);
            T_adj[v[j]].insert(u[j]);
        }
    }
    for (size_t idx = 0; idx < S_list.size(); idx++) {
        int i = S_list[idx];
        if (i == 0) continue;
        int pos = idx_in_S[i];
        if (get_P(radius[pos]) == 0 && T_adj[i].size() == 1) {
            int neighbor = *T_adj[i].begin();
            int ui = i, vi = neighbor;
            if (ui > vi) swap(ui, vi);
            auto it = edge_map.find({ui, vi});
            if (it == edge_map.end()) continue;
            int e_idx = it->second.first;
            ll edge_weight = it->second.second;
            S_list.erase(S_list.begin() + idx);
            idx_in_S.assign(N, -1);
            for (size_t pos2 = 0; pos2 < S_list.size(); pos2++)
                idx_in_S[S_list[pos2]] = pos2;
            radius.erase(radius.begin() + pos);
            edge_in_T[e_idx] = false;
            total_edge_weight -= edge_weight;
            total_rad_cost = 0;
            for (double r : radius) total_rad_cost += rad_cost(r);
            current_cost = total_rad_cost + total_edge_weight;
            T_adj.assign(N, set<int>());
            for (int j = 0; j < M; j++) {
                if (edge_in_T[j]) {
                    T_adj[u[j]].insert(v[j]);
                    T_adj[v[j]].insert(u[j]);
                }
            }
            idx = -1;
        }
    }

    edge_in_T.assign(M, false);
    total_edge_weight = 0;
    int T_size = S_list.size();
    if (T_size > 1) {
        vector<vector<ll>> term_dist(T_size, vector<ll>(T_size, INF_ll));
        for (int i = 0; i < T_size; i++) {
            for (int j = i+1; j < T_size; j++) {
                int a = S_list[i], b = S_list[j];
                term_dist[i][j] = term_dist[j][i] = dist_graph[a][b];
            }
        }
        vector<bool> in_mst(T_size, false);
        vector<ll> min_edge(T_size, INF_ll);
        vector<int> parent(T_size, -1);
        min_edge[0] = 0;
        for (int iter = 0; iter < T_size; iter++) {
            int u = -1;
            for (int i = 0; i < T_size; i++) {
                if (!in_mst[i] && (u == -1 || min_edge[i] < min_edge[u]))
                    u = i;
            }
            in_mst[u] = true;
            for (int v = 0; v < T_size; v++) {
                if (!in_mst[v] && term_dist[u][v] < min_edge[v]) {
                    min_edge[v] = term_dist[u][v];
                    parent[v] = u;
                }
            }
        }
        vector<int> dsu_parent(N);
        for (int i = 0; i < N; i++) dsu_parent[i] = i;
        function<int(int)> find = [&](int x) {
            if (dsu_parent[x] != x) dsu_parent[x] = find(dsu_parent[x]);
            return dsu_parent[x];
        };
        auto unite = [&](int x, int y) {
            x = find(x); y = find(y);
            if (x == y) return false;
            dsu_parent[x] = y;
            return true;
        };
        for (int i = 1; i < T_size; i++) {
            int a = S_list[i], b = S_list[parent[i]];
            vector<int> path_edges = get_path_edges(a, b);
            for (int e_idx : path_edges) {
                int uu = ::u[e_idx], vv = ::v[e_idx];
                if (unite(uu, vv)) {
                    edge_in_T[e_idx] = true;
                    total_edge_weight += w[e_idx];
                }
            }
        }
    }

    vector<int> P(N, 0);
    for (int i = 0; i < N; i++) {
        if (idx_in_S[i] != -1) {
            P[i] = get_P(radius[idx_in_S[i]]);
        }
    }
    for (int i = 0; i < N; i++) {
        cout << P[i] << (i == N-1 ? "\n" : " ");
    }
    for (int j = 0; j < M; j++) {
        cout << (edge_in_T[j] ? 1 : 0) << (j == M-1 ? "\n" : " ");
    }

    return 0;
}