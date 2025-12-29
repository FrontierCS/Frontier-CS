#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <queue>
#include <tuple>
#include <set>
#include <map>
#include <random>
#include <chrono>

using namespace std;

// Constants
const int MAX_P = 5000;
const long long INF_W = 1e18;

struct Edge {
    int u, v, w, id;
};

struct Resident {
    int x, y, id;
};

struct Station {
    int x, y, id;
};

int N, M, K;
vector<Station> stations;
vector<Edge> edges;
vector<Resident> residents;
vector<vector<pair<int, int>>> adj; // adj[u] = {v, edge_index}

// Precomputed data
long long dist_matrix[105][105]; // Shortest path distance between stations
int parent[105][105]; // parent[root][u] is the predecessor of u on path from root
int dist_resident_station[5005][105]; // Distance between resident k and station i (ceil)

// State
vector<int> assignment; // assignment[k] = station index

// Random number generator
mt19937 rng(12345);

long long get_dist_sq(int x1, int y1, int x2, int y2) {
    return 1LL * (x1 - x2) * (x1 - x2) + 1LL * (y1 - y2) * (y1 - y2);
}

int get_required_power(int x1, int y1, int x2, int y2) {
    long long sq = get_dist_sq(x1, y1, x2, y2);
    int r = sqrt(sq);
    while (1LL * r * r < sq) r++;
    return r;
}

// Dijkstra for APSP
void compute_apsp() {
    for (int i = 1; i <= N; ++i) {
        for (int j = 1; j <= N; ++j) {
            dist_matrix[i][j] = INF_W;
            parent[i][j] = 0;
        }
        dist_matrix[i][i] = 0;
        
        priority_queue<pair<long long, int>, vector<pair<long long, int>>, greater<pair<long long, int>>> pq;
        pq.push({0, i});
        
        while (!pq.empty()) {
            long long d = pq.top().first;
            int u = pq.top().second;
            pq.pop();
            
            if (d > dist_matrix[i][u]) continue;
            
            for (auto& edge_info : adj[u]) {
                int v = edge_info.first;
                int edge_idx = edge_info.second;
                int w = edges[edge_idx].w;
                if (dist_matrix[i][u] + w < dist_matrix[i][v]) {
                    dist_matrix[i][v] = dist_matrix[i][u] + w;
                    parent[i][v] = u; // Store predecessor
                    pq.push({dist_matrix[i][v], v});
                }
            }
        }
    }
}

// DSU structure for Kruskal's
struct DSU {
    vector<int> p;
    DSU(int n) {
        p.resize(n + 1);
        for (int i = 0; i <= n; ++i) p[i] = i;
    }
    int find(int x) {
        return p[x] == x ? x : p[x] = find(p[x]);
    }
    void unite(int x, int y) {
        int rx = find(x), ry = find(y);
        if (rx != ry) p[rx] = ry;
    }
};

// Calculate cost and determining edges
// Returns {total cost, boolean vector of active edges}
pair<long long, vector<bool>> evaluate(const vector<int>& current_assignment) {
    // 1. Calculate P and active stations
    vector<int> current_P(N + 1, 0);
    vector<bool> is_station_active(N + 1, false);
    is_station_active[1] = true; // Root always involved implicitly
    
    for (int k = 0; k < K; ++k) {
        int s = current_assignment[k];
        int d = dist_resident_station[k][s];
        if (d > current_P[s]) current_P[s] = d;
        is_station_active[s] = true;
    }
    
    long long power_cost = 0;
    vector<int> terminals;
    for (int i = 1; i <= N; ++i) {
        if (is_station_active[i]) {
            terminals.push_back(i);
            power_cost += 1LL * current_P[i] * current_P[i];
        }
    }
    
    // 2. Steiner Tree Approximation
    // Use Metric MST on terminals
    vector<tuple<long long, int, int>> metric_edges;
    int t_sz = terminals.size();
    if (t_sz <= 1) {
        return {power_cost, vector<bool>(M, false)};
    }

    // Build complete graph on terminals with shortest path distances
    for (int i = 0; i < t_sz; ++i) {
        for (int j = i + 1; j < t_sz; ++j) {
            int u = terminals[i];
            int v = terminals[j];
            metric_edges.emplace_back(dist_matrix[u][v], u, v);
        }
    }
    sort(metric_edges.begin(), metric_edges.end());
    
    DSU dsu_metric(N);
    vector<pair<int, int>> mst_virtual_edges;
    for (auto& edge : metric_edges) {
        int u = get<1>(edge);
        int v = get<2>(edge);
        if (dsu_metric.find(u) != dsu_metric.find(v)) {
            dsu_metric.unite(u, v);
            mst_virtual_edges.push_back({u, v});
        }
    }
    
    // Map back to real edges
    vector<int> candidate_edges;
    vector<bool> used_candidate(M, false);

    for (auto& ve : mst_virtual_edges) {
        int u = ve.first;
        int v = ve.second;
        // Reconstruct path from u to v
        int curr = v;
        while (curr != u) {
            int prev = parent[u][curr];
            int best_edge = -1;
            // Find edge between prev and curr with minimal weight
            long long min_w = INF_W;
            for (auto& edge_info : adj[prev]) {
                int next_node = edge_info.first;
                int idx = edge_info.second;
                if (next_node == curr) {
                    // We prefer the edge on the shortest path, but any minimal weight edge is fine for approximation
                    if (edges[idx].w < min_w) {
                        min_w = edges[idx].w;
                        best_edge = idx;
                    }
                    // If we want exact shortest path edge:
                    if (dist_matrix[u][prev] + edges[idx].w == dist_matrix[u][curr]) {
                        best_edge = idx;
                        break; 
                    }
                }
            }
            
            if (best_edge != -1 && !used_candidate[best_edge]) {
                used_candidate[best_edge] = true;
                candidate_edges.push_back(best_edge);
            }
            curr = prev;
        }
    }
    
    // Prune cycles in candidate edges by running MST again
    vector<pair<int, int>> final_edges_indices;
    for (int idx : candidate_edges) {
        final_edges_indices.push_back({edges[idx].w, idx});
    }
    sort(final_edges_indices.begin(), final_edges_indices.end());
    
    DSU dsu_real(N);
    vector<bool> final_active_edges(M, false);
    long long edge_cost = 0;
    
    for (auto& p : final_edges_indices) {
        int w = p.first;
        int idx = p.second;
        int u = edges[idx].u;
        int v = edges[idx].v;
        if (dsu_real.find(u) != dsu_real.find(v)) {
            dsu_real.unite(u, v);
            final_active_edges[idx] = true;
            edge_cost += w;
        }
    }
    
    return {power_cost + edge_cost, final_active_edges};
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> N >> M >> K)) return 0;
    
    stations.resize(N + 1);
    for (int i = 1; i <= N; ++i) {
        cin >> stations[i].x >> stations[i].y;
        stations[i].id = i;
    }
    
    edges.resize(M);
    adj.resize(N + 1);
    for (int i = 0; i < M; ++i) {
        cin >> edges[i].u >> edges[i].v >> edges[i].w;
        edges[i].id = i;
        adj[edges[i].u].push_back({edges[i].v, i});
        adj[edges[i].v].push_back({edges[i].u, i});
    }
    
    residents.resize(K);
    for (int i = 0; i < K; ++i) {
        cin >> residents[i].x >> residents[i].y;
        residents[i].id = i;
    }
    
    // Precompute distances
    compute_apsp();
    
    // Resident to Station distances
    for (int k = 0; k < K; ++k) {
        for (int i = 1; i <= N; ++i) {
            int d = get_required_power(residents[k].x, residents[k].y, stations[i].x, stations[i].y);
            dist_resident_station[k][i] = d;
        }
    }
    
    // Initial Assignment: Closest valid station
    assignment.resize(K);
    for (int k = 0; k < K; ++k) {
        int best_s = -1;
        int min_d = MAX_P + 1;
        for (int i = 1; i <= N; ++i) {
            int d = dist_resident_station[k][i];
            if (d <= MAX_P) {
                if (d < min_d) {
                    min_d = d;
                    best_s = i;
                }
            }
        }
        if (best_s == -1) best_s = 1; // Fallback
        assignment[k] = best_s;
    }
    
    auto current_res = evaluate(assignment);
    long long current_cost = current_res.first;
    vector<int> best_assignment = assignment;
    long long best_cost = current_cost;
    
    auto start_time = chrono::high_resolution_clock::now();
    double time_limit = 1.9;
    
    while (true) {
        auto now = chrono::high_resolution_clock::now();
        double elapsed = chrono::duration<double>(now - start_time).count();
        if (elapsed > time_limit) break;
        
        int type = rng() % 100;
        if (type < 30) { // 30% chance: Deactivate a station
            vector<int> counts(N + 1, 0);
            for(int s : assignment) counts[s]++;
            vector<int> active_stations;
            for(int i=1; i<=N; ++i) if(counts[i] > 0) active_stations.push_back(i);
            
            if (active_stations.empty()) continue;
            
            int u = active_stations[rng() % active_stations.size()];
            // Try to reassign residents of u
            vector<int> u_residents;
            for(int k=0; k<K; ++k) if(assignment[k] == u) u_residents.push_back(k);
            
            if(u_residents.empty()) continue;
            
            vector<int> backup_assignment = assignment;
            bool possible = true;
            for(int k : u_residents) {
                int best_v = -1;
                long long best_inc = INF_W;
                for(int v=1; v<=N; ++v) {
                    if (u == v) continue;
                    int d = dist_resident_station[k][v];
                    if (d > MAX_P) continue;
                    
                    // Simple heuristic: pick nearest valid
                    if (d < best_inc) {
                        best_inc = d;
                        best_v = v;
                    }
                }
                if (best_v == -1) { possible = false; break; }
                assignment[k] = best_v;
            }
            
            if (possible) {
                auto res = evaluate(assignment);
                if (res.first < current_cost) {
                    current_cost = res.first;
                    if (current_cost < best_cost) {
                        best_cost = current_cost;
                        best_assignment = assignment;
                    }
                } else {
                    assignment = backup_assignment;
                }
            } else {
                assignment = backup_assignment;
            }
            
        } else { // 70% chance: Move a resident
             int k = rng() % K;
             int u = assignment[k];
             int v = (rng() % N) + 1;
             if (u == v) continue;
             
             int d_v = dist_resident_station[k][v];
             if (d_v > MAX_P) continue;
             
             int backup = assignment[k];
             assignment[k] = v;
             
             auto res = evaluate(assignment);
             if (res.first < current_cost) {
                 current_cost = res.first;
                 if (current_cost < best_cost) {
                     best_cost = current_cost;
                     best_assignment = assignment;
                 }
             } else {
                 assignment[k] = backup;
             }
        }
    }
    
    // Final Output Generation
    auto final_res = evaluate(best_assignment);
    
    // Extract P
    vector<int> final_P(N + 1, 0);
    for (int k = 0; k < K; ++k) {
        int s = best_assignment[k];
        int d = dist_resident_station[k][s];
        if (d > final_P[s]) final_P[s] = d;
    }
    
    // Output
    for (int i = 1; i <= N; ++i) {
        cout << final_P[i] << (i == N ? "" : " ");
    }
    cout << "\n";
    for (int j = 0; j < M; ++j) {
        cout << (final_res.second[j] ? 1 : 0) << (j == M - 1 ? "" : " ");
    }
    cout << "\n";

    return 0;
}