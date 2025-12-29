#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <iomanip>
#include <random>
#include <chrono>

using namespace std;

const int INF = 1e9;

struct Point {
    int x, y;
};

struct Edge {
    int u, v, w, id;
};

int N, M, K;
vector<Point> stations;
vector<Edge> edges;
vector<Point> residents;
vector<vector<pair<int, int>>> adj; // u -> {v, edge_idx}

// Precomputed distances
int dist_mat[105][105]; // Shortest path distances between stations
int next_node[105][105]; // For path reconstruction: next_node[u][v] is next node from u to v
double res_dist[5005][105]; // Distance from resident k to station i

// Best solution
int best_P[105];
bool best_edge_active[305];
long long best_score = -1;

// Random engine
mt19937 rng(12345);

double get_dist(Point p1, Point p2) {
    return sqrt(pow(p1.x - p2.x, 2) + pow(p1.y - p2.y, 2));
}

void precompute() {
    // Initialize dist_mat
    for (int i = 1; i <= N; ++i) {
        for (int j = 1; j <= N; ++j) {
            if (i == j) dist_mat[i][j] = 0;
            else dist_mat[i][j] = INF;
            next_node[i][j] = 0;
        }
    }

    for (const auto& e : edges) {
        if (e.w < dist_mat[e.u][e.v]) {
            dist_mat[e.u][e.v] = e.w;
            dist_mat[e.v][e.u] = e.w;
            next_node[e.u][e.v] = e.v;
            next_node[e.v][e.u] = e.u;
        }
    }

    // Floyd-Warshall
    for (int k = 1; k <= N; ++k) {
        for (int i = 1; i <= N; ++i) {
            for (int j = 1; j <= N; ++j) {
                if (dist_mat[i][k] != INF && dist_mat[k][j] != INF) {
                    if (dist_mat[i][k] + dist_mat[k][j] < dist_mat[i][j]) {
                        dist_mat[i][j] = dist_mat[i][k] + dist_mat[k][j];
                        next_node[i][j] = next_node[i][k];
                    }
                }
            }
        }
    }

    // Resident distances
    for (int k = 0; k < K; ++k) {
        for (int i = 1; i <= N; ++i) {
            res_dist[k][i] = get_dist(residents[k], stations[i-1]);
        }
    }
}

// Union Find for MST
struct DSU {
    vector<int> parent;
    DSU(int n) {
        parent.resize(n + 1);
        for (int i = 0; i <= n; ++i) parent[i] = i;
    }
    int find(int i) {
        if (parent[i] == i) return i;
        return parent[i] = find(parent[i]);
    }
    void unite(int i, int j) {
        int root_i = find(i);
        int root_j = find(j);
        if (root_i != root_j) parent[root_i] = root_j;
    }
};

// Calculate tree cost and determine active edges for a set of terminals
long long solve_steiner(const vector<int>& p_vals, vector<bool>& out_edges) {
    vector<int> terminals;
    // Always include root
    terminals.push_back(1);
    for (int i = 2; i <= N; ++i) {
        if (p_vals[i] > 0) terminals.push_back(i);
    }

    // If only root, no edges
    if (terminals.size() == 1) {
        fill(out_edges.begin(), out_edges.end(), false);
        return 0;
    }

    // Metric closure MST approximation
    struct EdgeInfo {
        int u, v, w;
    };
    vector<EdgeInfo> m_edges;
    int T = terminals.size();
    
    for (int i = 0; i < T; ++i) {
        for (int j = i + 1; j < T; ++j) {
            int u = terminals[i];
            int v = terminals[j];
            m_edges.push_back({u, v, dist_mat[u][v]});
        }
    }
    sort(m_edges.begin(), m_edges.end(), [](const EdgeInfo& a, const EdgeInfo& b) {
        return a.w < b.w;
    });

    DSU dsu(N);
    fill(out_edges.begin(), out_edges.end(), false);
    
    // Mark edges on paths
    for (const auto& edge : m_edges) {
        if (dsu.find(edge.u) != dsu.find(edge.v)) {
            dsu.unite(edge.u, edge.v);
            
            // Reconstruct path
            int curr = edge.u;
            int target = edge.v;
            while (curr != target) {
                int nxt = next_node[curr][target];
                // Find the edge connecting curr and nxt with min weight that matches dist
                int best_e_idx = -1;
                int min_w = INF;
                
                for (auto& a : adj[curr]) {
                    if (a.first == nxt) {
                        int e_idx = a.second;
                        int w = edges[e_idx].w;
                        if (w < min_w) {
                            min_w = w;
                            best_e_idx = e_idx;
                        }
                    }
                }
                if (best_e_idx != -1) {
                    out_edges[best_e_idx] = true;
                }
                curr = nxt;
            }
        }
    }
    
    // Collect all selected edges
    vector<int> selected_indices;
    for (int i = 0; i < M; ++i) {
        if (out_edges[i]) selected_indices.push_back(i);
    }
    
    // Reset out_edges to fill only necessary ones
    fill(out_edges.begin(), out_edges.end(), false);
    long long tree_cost = 0;
    
    DSU dsu2(N);
    sort(selected_indices.begin(), selected_indices.end(), [&](int a, int b){
        return edges[a].w < edges[b].w;
    });
    
    // MST on subgraph
    vector<int> mst_edges;
    vector<vector<int>> tree_adj(N + 1);
    vector<int> degree(N + 1, 0);
    
    for (int idx : selected_indices) {
        int u = edges[idx].u;
        int v = edges[idx].v;
        if (dsu2.find(u) != dsu2.find(v)) {
            dsu2.unite(u, v);
            mst_edges.push_back(idx);
            tree_adj[u].push_back(idx);
            tree_adj[v].push_back(idx);
            degree[u]++;
            degree[v]++;
        }
    }
    
    // Prune non-terminal leaves
    vector<bool> is_terminal(N + 1, false);
    for (int t : terminals) is_terminal[t] = true;
    
    vector<int> q;
    for (int i = 1; i <= N; ++i) {
        if (degree[i] == 1 && !is_terminal[i]) {
            q.push_back(i);
        }
    }
    
    vector<bool> edge_removed(M, false);
    int head = 0;
    while(head < q.size()){
        int u = q[head++];
        for (int e_idx : tree_adj[u]) {
            if (edge_removed[e_idx]) continue;
            edge_removed[e_idx] = true;
            int v = (edges[e_idx].u == u) ? edges[e_idx].v : edges[e_idx].u;
            degree[v]--;
            if (degree[v] == 1 && !is_terminal[v]) {
                q.push_back(v);
            }
        }
    }
    
    for (int idx : mst_edges) {
        if (!edge_removed[idx]) {
            out_edges[idx] = true;
            tree_cost += edges[idx].w;
        }
    }
    
    return tree_cost;
}

void solve() {
    auto start_time = chrono::steady_clock::now();
    
    vector<int> order(K);
    for (int i = 0; i < K; ++i) order[i] = i;
    
    for(int i=0; i<edges.size(); ++i) {
        adj[edges[i].u].push_back({edges[i].v, i});
        adj[edges[i].v].push_back({edges[i].u, i});
    }

    while (true) {
        auto curr_time = chrono::steady_clock::now();
        if (chrono::duration_cast<chrono::milliseconds>(curr_time - start_time).count() > 1850) break;
        
        shuffle(order.begin(), order.end(), rng);
        
        vector<int> current_P(N + 1, 0);
        vector<int> s_conn_dist(N + 1, INF); 
        vector<bool> in_conn(N + 1, false);
        
        in_conn[1] = true;
        for (int i = 1; i <= N; ++i) s_conn_dist[i] = dist_mat[1][i];
        s_conn_dist[1] = 0;
        
        for (int k_idx : order) {
            bool covered = false;
            for (int i = 1; i <= N; ++i) {
                if (current_P[i] > 0 && current_P[i] >= ceil(res_dist[k_idx][i] - 1e-9)) {
                    covered = true;
                    break;
                }
            }
            if (covered) continue;
            
            int best_u = -1;
            long long min_cost = -1;
            
            for (int u = 1; u <= N; ++u) {
                double d = res_dist[k_idx][u];
                if (d > 5000) continue;
                int req = (int)ceil(d - 1e-9);
                if (req > 5000) continue;
                
                long long p_cost_diff = (long long)req * req - (long long)current_P[u] * current_P[u];
                long long conn_cost = s_conn_dist[u]; 
                
                long long total = p_cost_diff + conn_cost;
                
                if (best_u == -1 || total < min_cost) {
                    min_cost = total;
                    best_u = u;
                }
            }
            
            if (best_u != -1) {
                int req = (int)ceil(res_dist[k_idx][best_u] - 1e-9);
                current_P[best_u] = max(current_P[best_u], req);
                
                if (!in_conn[best_u]) {
                    int best_v = -1;
                    for (int i=1; i<=N; ++i) {
                        if (in_conn[i] && dist_mat[best_u][i] == s_conn_dist[best_u]) {
                            best_v = i;
                            break;
                        }
                    }
                    int curr = best_u;
                    while (!in_conn[curr]) {
                        in_conn[curr] = true;
                        for (int i=1; i<=N; ++i) {
                            if (!in_conn[i]) {
                                s_conn_dist[i] = min(s_conn_dist[i], dist_mat[curr][i]);
                            }
                        }
                        curr = next_node[curr][best_v];
                    }
                }
            }
        }
        
        vector<bool> current_edges(M, false);
        long long tree_cost = solve_steiner(current_P, current_edges);
        long long p_sum = 0;
        for(int i=1; i<=N; ++i) p_sum += (long long)current_P[i] * current_P[i];
        long long current_score = p_sum + tree_cost;
        
        // Shrink Phase
        bool improved = true;
        while (improved) {
            improved = false;
            vector<int> active_stations;
            for(int i=1; i<=N; ++i) if(current_P[i] > 0) active_stations.push_back(i);
            
            for (int u : active_stations) {
                int old_P = current_P[u];
                current_P[u] = 0;
                
                vector<int> lost_residents;
                for (int k=0; k<K; ++k) {
                    bool cov = false;
                    for (int i=1; i<=N; ++i) {
                        if (current_P[i] >= ceil(res_dist[k][i] - 1e-9)) {
                            cov = true; break;
                        }
                    }
                    if (!cov) lost_residents.push_back(k);
                }
                
                vector<int> backup_P = current_P;
                bool possible = true;
                
                for (int k_idx : lost_residents) {
                    int local_best = -1;
                    long long local_min = -1;
                    
                     for (int v = 1; v <= N; ++v) {
                        if (current_P[v] == 0 && v != 1) continue; 
                        
                        double d = res_dist[k_idx][v];
                        if (d > 5000) continue;
                        int req = (int)ceil(d - 1e-9);
                        if (req > 5000) continue;
                        
                        long long diff = (long long)req * req - (long long)current_P[v] * current_P[v];
                        
                        if (local_best == -1 || diff < local_min) {
                            local_min = diff;
                            local_best = v;
                        }
                     }
                     
                     if (local_best != -1) {
                         int req = (int)ceil(res_dist[k_idx][local_best] - 1e-9);
                         current_P[local_best] = max(current_P[local_best], req);
                     } else {
                         possible = false; break;
                     }
                }
                
                if (possible) {
                    vector<bool> temp_edges(M);
                    long long new_tree = solve_steiner(current_P, temp_edges);
                    long long new_p_sum = 0;
                    for(int i=1; i<=N; ++i) new_p_sum += (long long)current_P[i] * current_P[i];
                    long long new_score = new_p_sum + new_tree;
                    
                    if (new_score < current_score) {
                        current_score = new_score;
                        current_edges = temp_edges;
                        improved = true;
                    } else {
                        current_P = backup_P;
                        current_P[u] = old_P;
                    }
                } else {
                    current_P = backup_P;
                    current_P[u] = old_P;
                }
            }
        }
        
        if (best_score == -1 || current_score < best_score) {
            best_score = current_score;
            for(int i=1; i<=N; ++i) best_P[i] = current_P[i];
            for(int i=0; i<M; ++i) best_edge_active[i] = current_edges[i];
        }
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> N >> M >> K)) return 0;
    stations.resize(N);
    for (int i = 0; i < N; ++i) cin >> stations[i].x >> stations[i].y;
    edges.resize(M);
    adj.resize(N + 1);
    for (int i = 0; i < M; ++i) {
        cin >> edges[i].u >> edges[i].v >> edges[i].w;
        edges[i].id = i;
    }
    residents.resize(K);
    for (int i = 0; i < K; ++i) cin >> residents[i].x >> residents[i].y;

    precompute();
    solve();

    for (int i = 1; i <= N; ++i) cout << best_P[i] << (i == N ? "" : " ");
    cout << "\n";
    for (int i = 0; i < M; ++i) cout << (best_edge_active[i] ? 1 : 0) << (i == M - 1 ? "" : " ");
    cout << "\n";

    return 0;
}