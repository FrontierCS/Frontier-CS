#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>
#include <queue>
#include <set>
#include <map>
#include <limits>

using namespace std;

const long long INF = 1e18;
const double EPS = 1e-9;

int N, M, K;
vector<int> x, y;
vector<int> a, b;
vector<int> u, v;
vector<long long> w;
vector<vector<double>> dist_v_to_res;
vector<vector<long long>> distG;
vector<vector<int>> nxt;
vector<vector<int>> edge_id;
vector<vector<pair<int, long long>>> adj;

void dijkstra(int s, vector<long long>& dist, vector<int>& prev) {
    dist.assign(N, INF);
    prev.assign(N, -1);
    priority_queue<pair<long long, int>, vector<pair<long long, int>>, greater<pair<long long, int>>> pq;
    dist[s] = 0;
    pq.push({0, s});
    while (!pq.empty()) {
        auto [d, cur] = pq.top(); pq.pop();
        if (d > dist[cur]) continue;
        for (auto& [nxt, weight] : adj[cur]) {
            long long nd = d + weight;
            if (nd < dist[nxt]) {
                dist[nxt] = nd;
                prev[nxt] = cur;
                pq.push({nd, nxt});
            }
        }
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    cin >> N >> M >> K;
    x.resize(N); y.resize(N);
    for (int i = 0; i < N; i++) cin >> x[i] >> y[i];
    u.resize(M); v.resize(M); w.resize(M);
    adj.resize(N);
    edge_id.assign(N, vector<int>(N, -1));
    for (int j = 0; j < M; j++) {
        cin >> u[j] >> v[j] >> w[j];
        u[j]--; v[j]--;
        adj[u[j]].emplace_back(v[j], w[j]);
        adj[v[j]].emplace_back(u[j], w[j]);
        edge_id[u[j]][v[j]] = edge_id[v[j]][u[j]] = j;
    }
    a.resize(K); b.resize(K);
    for (int k = 0; k < K; k++) cin >> a[k] >> b[k];

    // precompute distances from vertices to residents
    dist_v_to_res.assign(N, vector<double>(K));
    for (int i = 0; i < N; i++) {
        for (int k = 0; k < K; k++) {
            double dx = x[i] - a[k];
            double dy = y[i] - b[k];
            dist_v_to_res[i][k] = sqrt(dx*dx + dy*dy);
        }
    }

    // all-pairs shortest paths and nxt matrix
    distG.assign(N, vector<long long>(N, INF));
    nxt.assign(N, vector<int>(N, -1));
    for (int i = 0; i < N; i++) {
        vector<long long> dist;
        vector<int> prev;
        dijkstra(i, dist, prev);
        for (int j = 0; j < N; j++) {
            distG[i][j] = dist[j];
            if (i == j) {
                nxt[i][j] = i;
                continue;
            }
            // find first step from i to j
            int cur = j;
            while (prev[cur] != i) {
                cur = prev[cur];
                if (cur == -1) break;
            }
            nxt[i][j] = cur;
        }
    }

    // initial assignment: each resident to closest vertex
    vector<int> assign(K);
    vector<vector<int>> residents_of(N);
    vector<double> r(N, 0.0);
    for (int k = 0; k < K; k++) {
        int best = 0;
        double best_dist = dist_v_to_res[0][k];
        for (int i = 1; i < N; i++) {
            if (dist_v_to_res[i][k] < best_dist) {
                best = i;
                best_dist = dist_v_to_res[i][k];
            }
        }
        assign[k] = best;
        residents_of[best].push_back(k);
    }
    for (int i = 0; i < N; i++) {
        if (!residents_of[i].empty()) {
            double maxd = 0.0;
            for (int k : residents_of[i]) {
                maxd = max(maxd, dist_v_to_res[i][k]);
            }
            r[i] = maxd;
        }
    }

    // Steiner tree function
    auto compute_steiner = [&](const set<int>& terminals, map<int, double>& attach_cost) -> pair<set<int>, double> {
        int root = 0;
        vector<bool> in_tree(N, false);
        set<int> tree_vertices;
        tree_vertices.insert(root);
        in_tree[root] = true;
        vector<long long> dist_to_tree(N, INF);
        vector<int> from(N, -1);
        // initialize distances to tree
        for (int v = 0; v < N; v++) {
            if (in_tree[v]) continue;
            for (int u : tree_vertices) {
                if (distG[v][u] < dist_to_tree[v]) {
                    dist_to_tree[v] = distG[v][u];
                    from[v] = u;
                }
            }
        }
        set<int> remaining_terminals = terminals;
        remaining_terminals.erase(root);
        set<int> tree_edges;
        double total_weight = 0.0;
        attach_cost.clear();
        while (!remaining_terminals.empty()) {
            // find closest terminal
            long long min_dist = INF;
            int t = -1;
            for (int v : remaining_terminals) {
                if (dist_to_tree[v] < min_dist) {
                    min_dist = dist_to_tree[v];
                    t = v;
                }
            }
            if (t == -1) break;
            attach_cost[t] = (double)min_dist;
            // add path from t to from[t]
            int cur = t;
            int target = from[t];
            while (cur != target) {
                int next_v = nxt[cur][target];
                int eid = edge_id[cur][next_v];
                if (eid == -1) {
                    cerr << "Error: no edge on shortest path" << endl;
                } else {
                    if (tree_edges.find(eid) == tree_edges.end()) {
                        tree_edges.insert(eid);
                        total_weight += w[eid];
                    }
                }
                if (!in_tree[cur]) {
                    in_tree[cur] = true;
                    tree_vertices.insert(cur);
                }
                cur = next_v;
            }
            // now cur == target is already in_tree
            // remove any terminals now in tree
            for (auto it = remaining_terminals.begin(); it != remaining_terminals.end(); ) {
                if (in_tree[*it]) {
                    it = remaining_terminals.erase(it);
                } else {
                    ++it;
                }
            }
            // update distances
            for (int v = 0; v < N; v++) {
                if (in_tree[v]) continue;
                dist_to_tree[v] = INF;
                for (int u : tree_vertices) {
                    if (distG[v][u] < dist_to_tree[v]) {
                        dist_to_tree[v] = distG[v][u];
                        from[v] = u;
                    }
                }
            }
        }
        return {tree_edges, total_weight};
    };

    set<int> T_set;
    for (int i = 0; i < N; i++) {
        if (r[i] > EPS) T_set.insert(i);
    }
    T_set.insert(0); // root always included

    map<int, double> attach_cost;
    auto [tree_edges, tree_cost] = compute_steiner(T_set, attach_cost);

    // merging iterations
    const int MAX_MERGE_ITER = 50;
    for (int iter = 0; iter < MAX_MERGE_ITER; iter++) {
        bool improved = false;
        vector<tuple<double, int, int>> candidates; // (delta, t, s)
        for (int t : T_set) {
            if (t == 0) continue; // do not merge root
            // find nearest terminal s (by graph distance) in T_set other than t
            int s = -1;
            long long best_dist = INF;
            for (int u : T_set) {
                if (u == t) continue;
                if (distG[t][u] < best_dist) {
                    best_dist = distG[t][u];
                    s = u;
                }
            }
            if (s == -1) continue;
            // compute new radius for s after merging t into s
            double new_r_s = r[s];
            for (int k : residents_of[t]) {
                double d = dist_v_to_res[s][k];
                if (d > new_r_s) new_r_s = d;
            }
            double delta_cover = new_r_s * new_r_s - r[s] * r[s] - r[t] * r[t];
            double delta_conn = -attach_cost[t];
            double delta = delta_cover + delta_conn;
            if (delta < -EPS) {
                candidates.emplace_back(delta, t, s);
            }
        }
        if (candidates.empty()) break;
        sort(candidates.begin(), candidates.end()); // most negative first
        for (auto& [delta, t, s] : candidates) {
            if (T_set.find(t) == T_set.end() || T_set.find(s) == T_set.end()) continue;
            // perform merge
            for (int k : residents_of[t]) {
                assign[k] = s;
                residents_of[s].push_back(k);
            }
            residents_of[t].clear();
            // update r[s]
            double new_r_s = r[s];
            for (int k : residents_of[s]) {
                double d = dist_v_to_res[s][k];
                if (d > new_r_s) new_r_s = d;
            }
            r[s] = new_r_s;
            r[t] = 0.0;
            T_set.erase(t);
            improved = true;
            break; // only one merge per iteration
        }
        if (!improved) break;
        // recompute Steiner tree
        tie(tree_edges, tree_cost) = compute_steiner(T_set, attach_cost);
    }

    // radius reduction and reassignment
    const int MAX_REDUCTION_ITER = 2;
    for (int red_iter = 0; red_iter < MAX_REDUCTION_ITER; red_iter++) {
        // compute unique coverage and reduce radii
        vector<double> new_r(N, 0.0);
        for (int i = 0; i < N; i++) {
            if (r[i] <= EPS) continue;
            double max_unique = 0.0;
            for (int k : residents_of[i]) {
                bool unique = true;
                for (int j = 0; j < N; j++) {
                    if (j == i || r[j] <= EPS) continue;
                    if (dist_v_to_res[j][k] <= r[j] + EPS) {
                        unique = false;
                        break;
                    }
                }
                if (unique) {
                    max_unique = max(max_unique, dist_v_to_res[i][k]);
                }
            }
            new_r[i] = max_unique;
        }
        r = new_r;
        // deactivate vertices with zero radius (except root)
        for (int i = 0; i < N; i++) {
            if (i != 0 && r[i] <= EPS) {
                residents_of[i].clear();
            }
        }
        // reassign all residents
        vector<vector<int>> new_residents_of(N);
        for (int k = 0; k < K; k++) {
            int best = -1;
            double best_dist = 1e9;
            // first try to find an active vertex that already covers it
            for (int i = 0; i < N; i++) {
                if (r[i] <= EPS) continue;
                double d = dist_v_to_res[i][k];
                if (d <= r[i] + EPS && d < best_dist) {
                    best = i;
                    best_dist = d;
                }
            }
            if (best == -1) {
                // if none, choose the closest active vertex
                for (int i = 0; i < N; i++) {
                    if (r[i] <= EPS) continue;
                    double d = dist_v_to_res[i][k];
                    if (d < best_dist) {
                        best = i;
                        best_dist = d;
                    }
                }
                // update r[best] to cover this resident
                if (best != -1) {
                    if (best_dist > r[best]) r[best] = best_dist;
                }
            }
            if (best == -1) best = 0; // fallback
            assign[k] = best;
            new_residents_of[best].push_back(k);
        }
        residents_of = new_residents_of;
        // update radii based on assignments
        for (int i = 0; i < N; i++) {
            if (residents_of[i].empty()) {
                r[i] = 0.0;
                continue;
            }
            double maxd = 0.0;
            for (int k : residents_of[i]) {
                maxd = max(maxd, dist_v_to_res[i][k]);
            }
            r[i] = maxd;
        }
        // update T_set
        T_set.clear();
        for (int i = 0; i < N; i++) {
            if (r[i] > EPS) T_set.insert(i);
        }
        T_set.insert(0);
        // recompute Steiner tree
        tie(tree_edges, tree_cost) = compute_steiner(T_set, attach_cost);
    }

    // finalize P_i and B_j
    vector<int> P(N, 0);
    for (int i = 0; i < N; i++) {
        if (r[i] > EPS) {
            P[i] = (int)ceil(r[i]);
            if (P[i] > 5000) P[i] = 5000;
        }
    }
    vector<int> B(M, 0);
    for (int eid : tree_edges) {
        B[eid] = 1;
    }

    // output
    for (int i = 0; i < N; i++) {
        cout << P[i] << (i == N-1 ? '\n' : ' ');
    }
    for (int j = 0; j < M; j++) {
        cout << B[j] << (j == M-1 ? '\n' : ' ');
    }

    return 0;
}