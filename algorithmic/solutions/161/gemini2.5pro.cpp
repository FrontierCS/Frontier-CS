#include <iostream>
#include <vector>
#include <cmath>
#include <numeric>
#include <algorithm>
#include <queue>
#include <set>
#include <random>
#include <chrono>
#include <tuple>

using namespace std;

const long long INF = 1e18;
const double TIME_LIMIT = 2.8;

struct Point {
    long long x, y;
};

long long dist_sq(Point p1, Point p2) {
    return (p1.x - p2.x) * (p1.x - p2.x) + (p1.y - p2.y) * (p1.y - p2.y);
}

struct Edge {
    int to;
    long long cost;
};

struct DSU {
    vector<int> parent;
    DSU(int n) {
        parent.resize(n + 1);
        iota(parent.begin(), parent.end(), 0);
    }
    int find(int i) {
        if (parent[i] == i) return i;
        return parent[i] = find(parent[i]);
    }
    void unite(int i, int j) {
        int root_i = find(i);
        int root_j = find(j);
        if (root_i != root_j) {
            parent[root_i] = root_j;
        }
    }
};

int N, M, K;
vector<Point> stations;
vector<Point> residents;
vector<tuple<int, int, int>> graph_edges;
vector<vector<Edge>> adj;
vector<vector<long long>> conn_cost;
vector<vector<int>> parent_paths;
vector<tuple<long long, int, int>> all_mst_edges;

auto start_time = chrono::high_resolution_clock::now();
mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

void dijkstra(int start_node) {
    conn_cost[start_node].assign(N + 1, INF);
    parent_paths[start_node].assign(N + 1, -1);
    conn_cost[start_node][start_node] = 0;
    priority_queue<pair<long long, int>, vector<pair<long long, int>>, greater<pair<long long, int>>> pq;
    pq.push({0, start_node});

    while (!pq.empty()) {
        auto [cost, u] = pq.top();
        pq.pop();

        if (cost > conn_cost[start_node][u]) continue;

        for (const auto& edge : adj[u]) {
            int v = edge.to;
            long long new_cost = cost + edge.cost;
            if (new_cost < conn_cost[start_node][v]) {
                conn_cost[start_node][v] = new_cost;
                parent_paths[start_node][v] = u;
                pq.push({new_cost, v});
            }
        }
    }
}

long long calculate_mst_cost_fast(const vector<bool>& is_active, int active_node_count) {
    if (active_node_count <= 1) return 0;
    
    DSU dsu(N);
    long long total_cost = 0;
    int edges_count = 0;
    
    for (const auto& edge : all_mst_edges) {
        auto [cost, u, v] = edge;
        if (is_active[u] && is_active[v]) {
            if (dsu.find(u) != dsu.find(v)) {
                dsu.unite(u, v);
                total_cost += cost;
                edges_count++;
                if (edges_count == active_node_count - 1) break;
            }
        }
    }
    return total_cost;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> N >> M >> K;
    stations.resize(N + 1);
    for (int i = 1; i <= N; ++i) cin >> stations[i].x >> stations[i].y;
    adj.resize(N + 1);
    graph_edges.resize(M);
    for (int i = 0; i < M; ++i) {
        int u, v, w;
        cin >> u >> v >> w;
        graph_edges[i] = {u, v, w};
        adj[u].push_back({v, (long long)w});
        adj[v].push_back({u, (long long)w});
    }
    residents.resize(K);
    for (int i = 0; i < K; ++i) cin >> residents[i].x >> residents[i].y;

    conn_cost.resize(N + 1);
    parent_paths.resize(N + 1);
    for (int i = 1; i <= N; ++i) dijkstra(i);
    
    for(int i = 1; i <= N; ++i) {
        for (int j = i + 1; j <= N; ++j) {
            all_mst_edges.emplace_back(conn_cost[i][j], i, j);
        }
    }
    sort(all_mst_edges.begin(), all_mst_edges.end());

    vector<vector<int>> station_resident_dist_ceil(N + 1, vector<int>(K));
    for (int i = 1; i <= N; ++i) {
        for (int j = 0; j < K; ++j) {
            station_resident_dist_ceil[i][j] = ceil(sqrt(dist_sq(stations[i], residents[j])));
        }
    }
    
    vector<vector<pair<long long, int>>> nearest_stations(K);
    for (int k = 0; k < K; ++k) {
        for (int i = 1; i <= N; ++i) {
            nearest_stations[k].push_back({dist_sq(stations[i], residents[k]), i});
        }
        sort(nearest_stations[k].begin(), nearest_stations[k].end());
    }

    vector<int> assignment(K);
    for (int k = 0; k < K; ++k) {
        assignment[k] = nearest_stations[k][0].second;
    }

    auto calculate_total_cost = [&](const vector<int>& current_assignment) {
        set<int> active_nodes_set;
        active_nodes_set.insert(1);
        vector<vector<int>> residents_by_station(N+1);
        for(int k=0; k<K; ++k){
            residents_by_station[current_assignment[k]].push_back(k);
        }
        
        long long power_cost = 0;
        for (int i = 1; i <= N; ++i) {
            if (!residents_by_station[i].empty()) {
                active_nodes_set.insert(i);
                long long max_dist = 0;
                for (int res_idx : residents_by_station[i]) {
                    max_dist = max(max_dist, (long long)station_resident_dist_ceil[i][res_idx]);
                }
                power_cost += max_dist * max_dist;
            }
        }
        
        vector<bool> is_active(N+1, false);
        for(int node : active_nodes_set) is_active[node] = true;
        long long connection_cost = calculate_mst_cost_fast(is_active, active_nodes_set.size());
        return power_cost + connection_cost;
    };

    long long current_cost = calculate_total_cost(assignment);
    vector<int> best_assignment = assignment;
    long long best_cost = current_cost;

    double start_temp = 2e6, end_temp = 1e2;

    while (true) {
        auto current_time = chrono::high_resolution_clock::now();
        double elapsed_sec = chrono::duration<double>(current_time - start_time).count();
        if (elapsed_sec > TIME_LIMIT) break;
        
        double progress = elapsed_sec / TIME_LIMIT;
        double temp = start_temp * pow(end_temp / start_temp, progress);

        int k = uniform_int_distribution<int>(0, K - 1)(rng);
        int old_station = assignment[k];
        
        int new_station;
        if (uniform_real_distribution<double>(0.0, 1.0)(rng) < 0.1) {
            new_station = uniform_int_distribution<int>(1, N)(rng);
        } else {
            int L = min((int)nearest_stations[k].size(), 10);
            int idx = uniform_int_distribution<int>(0, L - 1)(rng);
            new_station = nearest_stations[k][idx].second;
        }

        if (new_station == old_station) continue;

        vector<int> next_assignment = assignment;
        next_assignment[k] = new_station;
        long long next_cost = calculate_total_cost(next_assignment);

        if (next_cost < current_cost || uniform_real_distribution<double>(0.0, 1.0)(rng) < exp((double)(current_cost - next_cost) / temp)) {
            assignment = next_assignment;
            current_cost = next_cost;
            if (current_cost < best_cost) {
                best_cost = current_cost;
                best_assignment = assignment;
            }
        }
    }

    vector<int> p_out(N + 1, 0);
    vector<int> b_out(M, 0);

    set<int> final_active_nodes;
    final_active_nodes.insert(1);
    vector<vector<int>> final_residents_by_station(N+1);
    for(int k=0; k<K; ++k){
        final_residents_by_station[best_assignment[k]].push_back(k);
    }
    
    for (int i = 1; i <= N; ++i) {
        if (!final_residents_by_station[i].empty()) {
            final_active_nodes.insert(i);
            int max_dist = 0;
            for (int res_idx : final_residents_by_station[i]) {
                max_dist = max(max_dist, station_resident_dist_ceil[i][res_idx]);
            }
            p_out[i] = max_dist;
        }
    }

    if (final_active_nodes.size() > 1) {
        vector<bool> is_active(N+1, false);
        for(int node : final_active_nodes) is_active[node] = true;
        DSU dsu(N);
        int edges_count = 0;
        for (const auto& edge : all_mst_edges) {
            auto [cost, u, v] = edge;
            if (is_active[u] && is_active[v]) {
                if (dsu.find(u) != dsu.find(v)) {
                    dsu.unite(u, v);
                    int curr = v;
                    while (parent_paths[u][curr] != -1) {
                        int p = parent_paths[u][curr];
                        for(int i=0; i<M; ++i){
                            auto [e_u, e_v, w] = graph_edges[i];
                            if((e_u == curr && e_v == p) || (e_u == p && e_v == curr)){
                                b_out[i] = 1;
                                break;
                            }
                        }
                        curr = p;
                    }
                    edges_count++;
                    if (edges_count == (int)final_active_nodes.size() - 1) break;
                }
            }
        }
    }

    for (int i = 1; i <= N; ++i) {
        cout << p_out[i] << (i == N ? "" : " ");
    }
    cout << endl;
    for (int i = 0; i < M; ++i) {
        cout << b_out[i] << (i == M - 1 ? "" : " ");
    }
    cout << endl;

    return 0;
}