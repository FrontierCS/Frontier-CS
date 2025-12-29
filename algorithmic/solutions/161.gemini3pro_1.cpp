#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <iomanip>
#include <queue>
#include <set>
#include <map>
#include <random>
#include <chrono>

using namespace std;

// Constants
const int MAX_N = 105;
const int MAX_M = 305;
const int MAX_K = 5005;
const long long INF_LL = 1e18;

struct Point {
    int x, y;
};

struct Edge {
    int u, v, w, id;
};

int N, M, K;
Point stations[MAX_N];
Point residents[MAX_K];
vector<Edge> edges;
vector<pair<int, int>> adj[MAX_N]; // neighbor, edge_index

long long dist_matrix[MAX_N][MAX_N];
int next_node[MAX_N][MAX_N]; // For path reconstruction
vector<int> candidates[MAX_K]; // Valid stations for each resident
int station_resident_sq_dist[MAX_K][MAX_N]; // dist^2 from resident k to station i

// State
int assignment[MAX_K]; // Which station covers resident k
multiset<long long> station_dists[MAX_N]; // Stores d^2 for residents assigned to station i
bool edge_active[MAX_M]; // Is edge active (for final output)

// Random
mt19937 rng(1337);

long long dist_sq(Point p1, Point p2) {
    long long dx = p1.x - p2.x;
    long long dy = p1.y - p2.y;
    return dx * dx + dy * dy;
}

void compute_apsp() {
    for (int i = 1; i <= N; ++i) {
        for (int j = 1; j <= N; ++j) {
            dist_matrix[i][j] = (i == j) ? 0 : INF_LL;
            next_node[i][j] = -1;
        }
    }

    for (const auto& e : edges) {
        if (e.w < dist_matrix[e.u][e.v]) {
            dist_matrix[e.u][e.v] = e.w;
            dist_matrix[e.v][e.u] = e.w;
            next_node[e.u][e.v] = e.v;
            next_node[e.v][e.u] = e.u;
        }
    }

    for (int k = 1; k <= N; ++k) {
        for (int i = 1; i <= N; ++i) {
            for (int j = 1; j <= N; ++j) {
                if (dist_matrix[i][k] != INF_LL && dist_matrix[k][j] != INF_LL) {
                    if (dist_matrix[i][k] + dist_matrix[k][j] < dist_matrix[i][j]) {
                        dist_matrix[i][j] = dist_matrix[i][k] + dist_matrix[k][j];
                        next_node[i][j] = next_node[i][k];
                    }
                }
            }
        }
    }
}

// Recompute P_i^2 cost for a station based on its assigned residents
long long calc_station_power(int u) {
    if (station_dists[u].empty()) return 0;
    long long max_d_sq = *station_dists[u].rbegin();
    // Power must be integer >= sqrt(max_d_sq)
    // P_i = ceil(sqrt(max_d_sq))
    int P = 0;
    if (max_d_sq > 0) {
        P = (int)ceil(sqrt((double)max_d_sq));
    }
    return (long long)P * P;
}

// Helper to get actual power value
int get_power(int u) {
    if (station_dists[u].empty()) return 0;
    long long max_d_sq = *station_dists[u].rbegin();
    if (max_d_sq == 0) return 0;
    return (int)ceil(sqrt((double)max_d_sq));
}

// Get cost of Steiner Tree approximation for active nodes
// Does not modify global edge_active
long long compute_steiner_cost(const vector<int>& active_nodes) {
    if (active_nodes.empty()) return 0;
    // active_nodes should contain 1. If size is 1 (just node 1), cost is 0.
    if (active_nodes.size() == 1 && active_nodes[0] == 1) return 0;

    int k = active_nodes.size();
    vector<long long> min_dist(k, INF_LL);
    vector<int> parent(k, -1);
    vector<bool> visited(k, false);

    min_dist[0] = 0;
    
    vector<pair<int, int>> mst_edges;
    mst_edges.reserve(k);
    
    // Prim's algorithm on complete graph of active nodes
    for (int i = 0; i < k; ++i) {
        int u_idx = -1;
        long long best_d = INF_LL;
        
        for (int j = 0; j < k; ++j) {
            if (!visited[j] && min_dist[j] < best_d) {
                best_d = min_dist[j];
                u_idx = j;
            }
        }
        
        if (u_idx == -1) break;
        visited[u_idx] = true;
        
        if (parent[u_idx] != -1) {
            mst_edges.push_back({active_nodes[parent[u_idx]], active_nodes[u_idx]});
        }
        
        for (int v_idx = 0; v_idx < k; ++v_idx) {
            if (!visited[v_idx]) {
                long long d = dist_matrix[active_nodes[u_idx]][active_nodes[v_idx]];
                if (d < min_dist[v_idx]) {
                    min_dist[v_idx] = d;
                    parent[v_idx] = u_idx;
                }
            }
        }
    }
    
    // Reconstruct paths
    vector<int> used_edges; 
    static int edge_mark[MAX_M];
    static int mark_cnt = 0;
    mark_cnt++;

    long long cost = 0;
    
    // Adjacency for pruning
    static int deg[MAX_N];
    static vector<int> sub_adj[MAX_N];
    // Need to clear carefully
    // Since we only touch nodes involved in paths, we can clear them dynamically or just loop N
    // N=100 is small enough to loop
    for(int i=1; i<=N; ++i) {
        deg[i] = 0;
        sub_adj[i].clear();
    }
    
    for (auto& p : mst_edges) {
        int curr = p.first;
        int v = p.second;
        while (curr != v) {
            int nxt = next_node[curr][v];
            int best_e_idx = -1;
            
            // Find edge index
            for (auto& edge_info : adj[curr]) {
                if (edge_info.first == nxt) {
                    best_e_idx = edge_info.second;
                    break;
                }
            }
            
            if (best_e_idx != -1) {
                if (edge_mark[best_e_idx] != mark_cnt) {
                    edge_mark[best_e_idx] = mark_cnt;
                    cost += edges[best_e_idx].w;
                    used_edges.push_back(best_e_idx);
                    
                    deg[edges[best_e_idx].u]++;
                    deg[edges[best_e_idx].v]++;
                    sub_adj[edges[best_e_idx].u].push_back(best_e_idx);
                    sub_adj[edges[best_e_idx].v].push_back(best_e_idx);
                }
            }
            curr = nxt;
        }
    }
    
    // Pruning
    static bool is_target[MAX_N];
    for(int i=1; i<=N; ++i) is_target[i] = false;
    for(int u : active_nodes) is_target[u] = true;
    
    vector<int> q;
    for(int i=1; i<=N; ++i) {
        if (deg[i] == 1 && !is_target[i]) {
            q.push_back(i);
        }
    }
    
    int head = 0;
    while(head < q.size()){
        int u = q[head++];
        for(int e_idx : sub_adj[u]){
            if(edge_mark[e_idx] == mark_cnt){ // if edge is still in subgraph
                edge_mark[e_idx] = mark_cnt - 1; // Unmark/Remove
                cost -= edges[e_idx].w;
                
                int v = (edges[e_idx].u == u) ? edges[e_idx].v : edges[e_idx].u;
                deg[v]--;
                if(deg[v] == 1 && !is_target[v]){
                    q.push_back(v);
                }
            }
        }
    }

    return cost;
}

// Function to set global edge_active based on current assignment
void update_global_edges() {
    vector<int> active;
    active.push_back(1);
    for (int i = 1; i <= N; ++i) {
        if (!station_dists[i].empty()) {
            if (i != 1) active.push_back(i);
        }
    }
    
    for(int j=0; j<M; ++j) edge_active[j] = false;
    
    if (active.size() <= 1 && active[0] == 1) return;
    
    // Copy-paste logic from compute_steiner_cost but update edge_active
    int k = active.size();
    vector<long long> min_dist(k, INF_LL);
    vector<int> parent(k, -1);
    vector<bool> visited(k, false);
    min_dist[0] = 0;
    
    vector<pair<int, int>> mst_edges;
    
    for (int i = 0; i < k; ++i) {
        int u_idx = -1;
        long long best_d = INF_LL;
        for (int j = 0; j < k; ++j) {
            if (!visited[j] && min_dist[j] < best_d) {
                best_d = min_dist[j];
                u_idx = j;
            }
        }
        if (u_idx == -1) break;
        visited[u_idx] = true;
        if (parent[u_idx] != -1) {
            mst_edges.push_back({active[parent[u_idx]], active[u_idx]});
        }
        for (int v_idx = 0; v_idx < k; ++v_idx) {
            if (!visited[v_idx]) {
                long long d = dist_matrix[active[u_idx]][active[v_idx]];
                if (d < min_dist[v_idx]) {
                    min_dist[v_idx] = d;
                    parent[v_idx] = u_idx;
                }
            }
        }
    }
    
    static int deg[MAX_N];
    static vector<int> sub_adj[MAX_N];
    for(int i=1; i<=N; ++i) {
        deg[i] = 0;
        sub_adj[i].clear();
    }
    
    for (auto& p : mst_edges) {
        int curr = p.first;
        int v = p.second;
        while (curr != v) {
            int nxt = next_node[curr][v];
            int best_e_idx = -1;
            for (auto& edge_info : adj[curr]) {
                if (edge_info.first == nxt) {
                    best_e_idx = edge_info.second;
                    break;
                }
            }
            if (best_e_idx != -1 && !edge_active[best_e_idx]) {
                edge_active[best_e_idx] = true;
                deg[edges[best_e_idx].u]++;
                deg[edges[best_e_idx].v]++;
                sub_adj[edges[best_e_idx].u].push_back(best_e_idx);
                sub_adj[edges[best_e_idx].v].push_back(best_e_idx);
            }
            curr = nxt;
        }
    }
    
    static bool is_target[MAX_N];
    for(int i=1; i<=N; ++i) is_target[i] = false;
    for(int u : active) is_target[u] = true;
    
    vector<int> q;
    for(int i=1; i<=N; ++i) {
        if (deg[i] == 1 && !is_target[i]) {
            q.push_back(i);
        }
    }
    
    int head = 0;
    while(head < q.size()){
        int u = q[head++];
        for(int e_idx : sub_adj[u]){
            if(edge_active[e_idx]){
                edge_active[e_idx] = false;
                int v = (edges[e_idx].u == u) ? edges[e_idx].v : edges[e_idx].u;
                deg[v]--;
                if(deg[v] == 1 && !is_target[v]){
                    q.push_back(v);
                }
            }
        }
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    auto start_time = chrono::steady_clock::now();
    
    if (!(cin >> N >> M >> K)) return 0;
    for (int i = 1; i <= N; ++i) {
        cin >> stations[i].x >> stations[i].y;
    }
    for (int i = 0; i < M; ++i) {
        int u, v, w;
        cin >> u >> v >> w;
        edges.push_back({u, v, w, i});
        adj[u].push_back({v, i});
        adj[v].push_back({u, i});
    }
    for (int i = 0; i < K; ++i) {
        cin >> residents[i].x >> residents[i].y;
    }

    compute_apsp();

    for (int i = 0; i < K; ++i) {
        for (int j = 1; j <= N; ++j) {
            long long d2 = dist_sq(residents[i], stations[j]);
            station_resident_sq_dist[i][j] = d2;
            if (d2 <= 5000LL * 5000LL) {
                candidates[i].push_back(j);
            }
        }
    }

    // Initial Assignment: closest station
    for (int i = 0; i < K; ++i) {
        int best_s = -1;
        long long best_metric = INF_LL;
        
        for (int s : candidates[i]) {
            long long d = station_resident_sq_dist[i][s];
            if (d < best_metric) {
                best_metric = d;
                best_s = s;
            }
        }
        
        assignment[i] = best_s;
        station_dists[best_s].insert(station_resident_sq_dist[i][best_s]);
    }
    
    long long current_power_cost = 0;
    for (int i = 1; i <= N; ++i) {
        current_power_cost += calc_station_power(i);
    }
    
    vector<int> active_nodes;
    active_nodes.reserve(N);
    active_nodes.push_back(1);
    for(int i=1; i<=N; ++i) {
        if(!station_dists[i].empty() && i != 1) active_nodes.push_back(i);
    }
    long long current_conn_cost = compute_steiner_cost(active_nodes);
    
    // Optimization loop
    double time_limit = 1.9;
    int iter = 0;
    
    vector<int> new_active_nodes;
    new_active_nodes.reserve(N);

    while (true) {
        iter++;
        if ((iter & 255) == 0) {
            auto curr_time = chrono::steady_clock::now();
            chrono::duration<double> elapsed = curr_time - start_time;
            if (elapsed.count() > time_limit) break;
        }

        int r = uniform_int_distribution<int>(0, K-1)(rng);
        int old_s = assignment[r];
        if (candidates[r].empty()) continue; 
        
        int idx = uniform_int_distribution<int>(0, candidates[r].size() - 1)(rng);
        int new_s = candidates[r][idx];
        
        if (old_s == new_s) continue;
        
        long long old_power_cost_old_s = calc_station_power(old_s);
        long long old_power_cost_new_s = calc_station_power(new_s);
        
        // Remove from old_s
        station_dists[old_s].erase(station_dists[old_s].find(station_resident_sq_dist[r][old_s]));
        // Add to new_s
        station_dists[new_s].insert(station_resident_sq_dist[r][new_s]);
        
        long long new_power_cost_old_s = calc_station_power(old_s);
        long long new_power_cost_new_s = calc_station_power(new_s);
        
        long long power_delta = (new_power_cost_old_s + new_power_cost_new_s) - (old_power_cost_old_s + old_power_cost_new_s);
        
        bool old_s_was_active = (old_power_cost_old_s > 0);
        bool new_s_was_active = (old_power_cost_new_s > 0);
        bool old_s_is_active = (new_power_cost_old_s > 0);
        bool new_s_is_active = (new_power_cost_new_s > 0);
        
        long long conn_delta = 0;
        bool active_set_changed = false;
        
        if (old_s != 1 && old_s_was_active && !old_s_is_active) active_set_changed = true;
        if (new_s != 1 && !new_s_was_active && new_s_is_active) active_set_changed = true;
        
        if (active_set_changed) {
            new_active_nodes.clear();
            new_active_nodes.push_back(1);
            for (int i = 1; i <= N; ++i) {
                if (!station_dists[i].empty() && i != 1) {
                    new_active_nodes.push_back(i);
                }
            }
            long long new_conn_cost = compute_steiner_cost(new_active_nodes);
            conn_delta = new_conn_cost - current_conn_cost;
        }
        
        long long total_delta = power_delta + conn_delta;
        
        if (total_delta <= 0) {
            // Accept
            assignment[r] = new_s;
            current_power_cost += power_delta;
            current_conn_cost += conn_delta;
        } else {
            // Reject: Revert
            station_dists[new_s].erase(station_dists[new_s].find(station_resident_sq_dist[r][new_s]));
            station_dists[old_s].insert(station_resident_sq_dist[r][old_s]);
        }
    }

    for (int i = 1; i <= N; ++i) {
        cout << get_power(i) << (i == N ? "" : " ");
    }
    cout << "\n";
    
    update_global_edges();
    for (int j = 0; j < M; ++j) {
        cout << (edge_active[j] ? 1 : 0) << (j == M - 1 ? "" : " ");
    }
    cout << "\n";

    return 0;
}