#include <bits/stdc++.h>
using namespace std;
using ll = long long;
using pii = pair<int, int>;

const double INF_DOUBLE = 1e18;
const ll INF_LL = 1e18;
const int MAX_N = 100;
const int MAX_K = 5000;

struct Point {
    int x, y;
    Point() {}
    Point(int x, int y) : x(x), y(y) {}
};

double euclid(const Point& a, const Point& b) {
    double dx = a.x - b.x;
    double dy = a.y - b.y;
    return sqrt(dx*dx + dy*dy);
}

int iceil(double x) {
    int v = (int)floor(x);
    if (v < x - 1e-9) v++;
    return v;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M, K;
    cin >> N >> M >> K;

    vector<Point> stations(N);
    for (int i = 0; i < N; i++) {
        cin >> stations[i].x >> stations[i].y;
    }

    vector<tuple<int, int, ll>> edges(M);
    map<pii, int> edgeIndex;
    for (int j = 0; j < M; j++) {
        int u, v;
        ll w;
        cin >> u >> v >> w;
        u--; v--;
        edges[j] = {u, v, w};
        if (u > v) swap(u, v);
        edgeIndex[{u, v}] = j;
    }

    vector<Point> residents(K);
    for (int k = 0; k < K; k++) {
        cin >> residents[k].x >> residents[k].y;
    }

    // Precompute distances from stations to residents
    vector<vector<double>> dist_sr(N, vector<double>(K));
    vector<vector<int>> resident_sorted(K);
    for (int k = 0; k < K; k++) {
        vector<pair<double, int>> list;
        for (int i = 0; i < N; i++) {
            double d = euclid(stations[i], residents[k]);
            dist_sr[i][k] = d;
            list.emplace_back(d, i);
        }
        sort(list.begin(), list.end());
        resident_sorted[k].resize(N);
        for (int idx = 0; idx < N; idx++) {
            resident_sorted[k][idx] = list[idx].second;
        }
    }

    // All-pairs shortest paths on graph (edge weights)
    vector<vector<ll>> graph_dist(N, vector<ll>(N, INF_LL));
    vector<vector<int>> graph_next(N, vector<int>(N, -1));
    for (int i = 0; i < N; i++) graph_dist[i][i] = 0;
    for (int j = 0; j < M; j++) {
        auto [u, v, w] = edges[j];
        if (w < graph_dist[u][v]) {
            graph_dist[u][v] = graph_dist[v][u] = w;
            graph_next[u][v] = v;
            graph_next[v][u] = u;
        }
    }
    // Floyd-Warshall
    for (int k = 0; k < N; k++) {
        for (int i = 0; i < N; i++) {
            if (graph_dist[i][k] == INF_LL) continue;
            for (int j = 0; j < N; j++) {
                if (graph_dist[k][j] == INF_LL) continue;
                ll nd = graph_dist[i][k] + graph_dist[k][j];
                if (nd < graph_dist[i][j]) {
                    graph_dist[i][j] = nd;
                    graph_next[i][j] = graph_next[i][k];
                }
            }
        }
    }

    // Helper: get shortest path from a to b
    auto get_path = [&](int a, int b) -> vector<int> {
        if (graph_next[a][b] == -1) return {};
        vector<int> path;
        path.push_back(a);
        while (a != b) {
            a = graph_next[a][b];
            path.push_back(a);
        }
        return path;
    };

    // Initial assignment: each resident to closest station
    vector<vector<double>> station_dists(N);
    for (int k = 0; k < K; k++) {
        int best = resident_sorted[k][0];
        station_dists[best].push_back(dist_sr[best][k]);
    }

    vector<int> Pi(N, 0);
    for (int i = 0; i < N; i++) {
        if (!station_dists[i].empty()) {
            double maxd = *max_element(station_dists[i].begin(), station_dists[i].end());
            Pi[i] = iceil(maxd);
        }
    }

    // Terminals: stations with Pi>0 plus root (0)
    set<int> terminals;
    for (int i = 0; i < N; i++) {
        if (Pi[i] > 0) terminals.insert(i);
    }
    terminals.insert(0);

    // Steiner tree heuristic (shortest path heuristic)
    vector<bool> in_tree(N, false);
    in_tree[0] = true;
    set<pii> tree_edges_set; // store as (min, max)

    int remaining = 0;
    for (int t : terminals) if (!in_tree[t]) remaining++;
    while (remaining > 0) {
        ll best_d = INF_LL;
        int best_v = -1, best_t = -1;
        for (int t : terminals) {
            if (in_tree[t]) continue;
            for (int v = 0; v < N; v++) {
                if (in_tree[v] && graph_dist[v][t] < best_d) {
                    best_d = graph_dist[v][t];
                    best_v = v;
                    best_t = t;
                }
            }
        }
        if (best_t == -1) break;
        vector<int> path = get_path(best_v, best_t);
        int idx = (int)path.size() - 1;
        while (idx >= 0 && !in_tree[path[idx]]) {
            int u = path[idx];
            in_tree[u] = true;
            if (idx > 0) {
                int v = path[idx-1];
                int a = min(u, v), b = max(u, v);
                tree_edges_set.insert({a, b});
            }
            idx--;
        }
        remaining = 0;
        for (int t : terminals) if (!in_tree[t]) remaining++;
    }

    // Reassign residents to stations in the tree
    station_dists.assign(N, vector<double>());
    for (int k = 0; k < K; k++) {
        double best_d = INF_DOUBLE;
        int best_i = -1;
        for (int i = 0; i < N; i++) {
            if (!in_tree[i]) continue;
            double d = dist_sr[i][k];
            if (d < best_d) {
                best_d = d;
                best_i = i;
            }
        }
        if (best_i != -1) {
            station_dists[best_i].push_back(best_d);
        }
    }
    // Update Pi based on new assignment
    Pi.assign(N, 0);
    for (int i = 0; i < N; i++) {
        if (!station_dists[i].empty()) {
            double maxd = *max_element(station_dists[i].begin(), station_dists[i].end());
            Pi[i] = iceil(maxd);
        }
    }

    // Prune leaves with Pi==0 (except root)
    for (int iter = 0; iter < 2; iter++) {
        // Build adjacency from tree_edges_set
        vector<set<int>> adj(N);
        for (auto& e : tree_edges_set) {
            int u = e.first, v = e.second;
            adj[u].insert(v);
            adj[v].insert(u);
        }
        queue<int> leaf_q;
        for (int i = 0; i < N; i++) {
            if (i != 0 && in_tree[i] && adj[i].size() == 1 && Pi[i] == 0) {
                leaf_q.push(i);
            }
        }
        while (!leaf_q.empty()) {
            int u = leaf_q.front(); leaf_q.pop();
            if (adj[u].size() != 1 || Pi[u] != 0) continue;
            int v = *adj[u].begin();
            adj[u].erase(v);
            adj[v].erase(u);
            in_tree[u] = false;
            int a = min(u, v), b = max(u, v);
            tree_edges_set.erase({a, b});
            if (v != 0 && adj[v].size() == 1 && Pi[v] == 0) {
                leaf_q.push(v);
            }
        }

        // Reassign residents again after pruning
        station_dists.assign(N, vector<double>());
        for (int k = 0; k < K; k++) {
            double best_d = INF_DOUBLE;
            int best_i = -1;
            for (int i = 0; i < N; i++) {
                if (!in_tree[i]) continue;
                double d = dist_sr[i][k];
                if (d < best_d) {
                    best_d = d;
                    best_i = i;
                }
            }
            if (best_i != -1) {
                station_dists[best_i].push_back(best_d);
            }
        }
        Pi.assign(N, 0);
        for (int i = 0; i < N; i++) {
            if (!station_dists[i].empty()) {
                double maxd = *max_element(station_dists[i].begin(), station_dists[i].end());
                Pi[i] = iceil(maxd);
            }
        }
    }

    // Local search: try to move residents to other stations in the tree
    vector<int> assign(K, -1);
    for (int k = 0; k < K; k++) {
        double best_d = INF_DOUBLE;
        int best_i = -1;
        for (int i = 0; i < N; i++) {
            if (!in_tree[i]) continue;
            double d = dist_sr[i][k];
            if (d < best_d) {
                best_d = d;
                best_i = i;
            }
        }
        assign[k] = best_i;
    }
    // station_dists is already set from previous step

    // Precompute for each station max1 and max2
    vector<double> max1(N, 0), max2(N, 0);
    for (int i = 0; i < N; i++) {
        if (station_dists[i].empty()) continue;
        double m1 = 0, m2 = 0;
        for (double d : station_dists[i]) {
            if (d > m1) {
                m2 = m1;
                m1 = d;
            } else if (d > m2) {
                m2 = d;
            }
        }
        max1[i] = m1;
        max2[i] = m2;
    }

    // Random generator
    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

    for (int pass = 0; pass < 5; pass++) {
        vector<int> order(K);
        iota(order.begin(), order.end(), 0);
        shuffle(order.begin(), order.end(), rng);

        for (int idx : order) {
            int i = assign[idx];
            if (i == -1) continue;
            double d_i = dist_sr[i][idx];
            // Consider moving to other stations in tree (up to 10 closest)
            int checked = 0;
            for (int rank = 0; rank < N && checked < 10; rank++) {
                int j = resident_sorted[idx][rank];
                if (!in_tree[j] || j == i) continue;
                checked++;
                double d_j = dist_sr[j][idx];

                // Compute new max for i after removing d_i
                double new_max_i;
                if (station_dists[i].size() == 1) {
                    new_max_i = 0;
                } else {
                    if (abs(d_i - max1[i]) < 1e-9) {
                        new_max_i = max2[i];
                    } else {
                        new_max_i = max1[i];
                    }
                }
                // Compute new max for j after adding d_j
                double new_max_j = max(max1[j], d_j);

                int old_Pi_i = iceil(max1[i]);
                int old_Pi_j = iceil(max1[j]);
                int new_Pi_i = iceil(new_max_i);
                int new_Pi_j = iceil(new_max_j);

                ll delta = (ll)new_Pi_i*new_Pi_i - (ll)old_Pi_i*old_Pi_i
                         + (ll)new_Pi_j*new_Pi_j - (ll)old_Pi_j*old_Pi_j;

                if (delta < 0) {
                    // Perform move
                    // Remove from i
                    auto it = find(station_dists[i].begin(), station_dists[i].end(), d_i);
                    if (it != station_dists[i].end()) station_dists[i].erase(it);
                    // Add to j
                    station_dists[j].push_back(d_j);

                    // Recompute max1/max2 for i and j
                    double m1 = 0, m2 = 0;
                    for (double d : station_dists[i]) {
                        if (d > m1) { m2 = m1; m1 = d; }
                        else if (d > m2) m2 = d;
                    }
                    max1[i] = m1; max2[i] = m2;
                    Pi[i] = iceil(m1);

                    m1 = 0; m2 = 0;
                    for (double d : station_dists[j]) {
                        if (d > m1) { m2 = m1; m1 = d; }
                        else if (d > m2) m2 = d;
                    }
                    max1[j] = m1; max2[j] = m2;
                    Pi[j] = iceil(m1);

                    assign[idx] = j;
                    break; // move accepted, move to next resident
                }
            }
        }
    }

    // Final prune after local search
    {
        vector<set<int>> adj(N);
        for (auto& e : tree_edges_set) {
            int u = e.first, v = e.second;
            adj[u].insert(v);
            adj[v].insert(u);
        }
        queue<int> leaf_q;
        for (int i = 0; i < N; i++) {
            if (i != 0 && in_tree[i] && adj[i].size() == 1 && Pi[i] == 0) {
                leaf_q.push(i);
            }
        }
        while (!leaf_q.empty()) {
            int u = leaf_q.front(); leaf_q.pop();
            if (adj[u].size() != 1 || Pi[u] != 0) continue;
            int v = *adj[u].begin();
            adj[u].erase(v);
            adj[v].erase(u);
            in_tree[u] = false;
            int a = min(u, v), b = max(u, v);
            tree_edges_set.erase({a, b});
            if (v != 0 && adj[v].size() == 1 && Pi[v] == 0) {
                leaf_q.push(v);
            }
        }
    }

    // Ensure all residents are assigned to stations in the tree (should be)
    // Recompute Pi for stations in tree based on final assignment (optional, but we already have Pi updated)

    // Output
    for (int i = 0; i < N; i++) {
        cout << Pi[i];
        if (i < N-1) cout << " ";
    }
    cout << "\n";

    for (int j = 0; j < M; j++) {
        auto [u, v, w] = edges[j];
        int a = min(u, v), b = max(u, v);
        if (tree_edges_set.count({a, b})) {
            cout << 1;
        } else {
            cout << 0;
        }
        if (j < M-1) cout << " ";
    }
    cout << endl;

    return 0;
}