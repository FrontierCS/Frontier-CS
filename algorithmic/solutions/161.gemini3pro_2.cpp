#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <set>
#include <map>
#include <random>
#include <chrono>

using namespace std;

const long long INF_LL = 1e18;

struct Point {
    int x, y;
};

struct Edge {
    int u, v;
    long long w;
    int id;
};

struct Resident {
    int x, y;
    int id;
};

int N, M, K;
vector<Point> stations;
vector<Edge> edges;
vector<Resident> residents;
vector<vector<pair<int, long long>>> adj;
long long dist_mat[105][105];
int next_hop[105][105];
int res_to_station_req[5005][105]; 

vector<int> assignment; 
vector<multiset<int>> station_reqs; 
vector<int> P; 
vector<bool> tree_nodes; 
vector<int> current_edges; 
long long current_score = INF_LL;

mt19937 rng(0);

long long dist_sq_res(int s_idx, int r_idx) {
    long long dx = stations[s_idx].x - residents[r_idx].x;
    long long dy = stations[s_idx].y - residents[r_idx].y;
    return dx * dx + dy * dy;
}

void floyd_warshall() {
    for (int i = 1; i <= N; ++i) {
        for (int j = 1; j <= N; ++j) {
            dist_mat[i][j] = (i == j) ? 0 : INF_LL;
            next_hop[i][j] = (i == j) ? i : 0;
        }
    }
    for (const auto& e : edges) {
        if (e.w < dist_mat[e.u][e.v]) {
            dist_mat[e.u][e.v] = e.w;
            dist_mat[e.v][e.u] = e.w;
            next_hop[e.u][e.v] = e.v;
            next_hop[e.v][e.u] = e.u;
        }
    }

    for (int k = 1; k <= N; ++k) {
        for (int i = 1; i <= N; ++i) {
            for (int j = 1; j <= N; ++j) {
                if (dist_mat[i][k] != INF_LL && dist_mat[k][j] != INF_LL) {
                    if (dist_mat[i][k] + dist_mat[k][j] < dist_mat[i][j]) {
                        dist_mat[i][j] = dist_mat[i][k] + dist_mat[k][j];
                        next_hop[i][j] = next_hop[i][k];
                    }
                }
            }
        }
    }
}

long long build_steiner_tree(const vector<int>& active_stations, vector<int>& out_edges, vector<bool>& out_tree_nodes) {
    out_edges.clear();
    out_tree_nodes.assign(N + 1, false);
    
    vector<int> tree_members;
    tree_members.push_back(1);
    out_tree_nodes[1] = true;
    
    vector<bool> is_target(N + 1, false);
    int target_count = 0;
    for (int s : active_stations) {
        if (!out_tree_nodes[s]) {
            is_target[s] = true;
            target_count++;
        }
    }
    
    vector<bool> edge_used(M + 1, false);
    long long cable_cost = 0;
    vector<int> path_edges;

    while (target_count > 0) {
        long long best_dist = INF_LL;
        int best_u = -1; 
        int best_v = -1; 
        
        for (int i = 1; i <= N; ++i) {
            if (is_target[i]) {
                for (int u : tree_members) {
                    if (dist_mat[u][i] < best_dist) {
                        best_dist = dist_mat[u][i];
                        best_u = u;
                        best_v = i;
                    }
                }
            }
        }
        
        if (best_u == -1) break; 
        
        int curr = best_u;
        int dest = best_v;
        
        while (curr != dest) {
            int nxt = next_hop[curr][dest];
            int edge_idx = -1;
            long long min_w = INF_LL;
            for (auto& edge : edges) {
                if ((edge.u == curr && edge.v == nxt) || (edge.u == nxt && edge.v == curr)) {
                    if (edge.w < min_w) {
                        min_w = edge.w;
                        edge_idx = edge.id;
                    }
                }
            }
            if (!edge_used[edge_idx]) {
                edge_used[edge_idx] = true;
                path_edges.push_back(edge_idx);
            }
            curr = nxt;
            if (!out_tree_nodes[curr]) {
                out_tree_nodes[curr] = true;
                tree_members.push_back(curr);
                if (is_target[curr]) {
                    is_target[curr] = false;
                    target_count--;
                }
            }
        }
    }
    
    struct DSU {
        vector<int> p;
        DSU(int n) { p.resize(n + 1); for(int i=0; i<=n; ++i) p[i]=i; }
        int find(int x) { return p[x]==x ? x : p[x]=find(p[x]); }
        bool unite(int x, int y) {
            int rx = find(x), ry = find(y);
            if(rx!=ry) { p[rx]=ry; return true; }
            return false;
        }
    };
    
    sort(path_edges.begin(), path_edges.end(), [&](int a, int b) {
        return edges[a-1].w < edges[b-1].w;
    });
    
    DSU dsu(N);
    vector<int> mst_edges;
    long long mst_weight = 0;
    
    for (int eid : path_edges) {
        if (dsu.unite(edges[eid-1].u, edges[eid-1].v)) {
            mst_edges.push_back(eid);
            mst_weight += edges[eid-1].w;
        }
    }
    
    set<int> active_edge_set(mst_edges.begin(), mst_edges.end());
    vector<bool> is_required(N + 1, false);
    is_required[1] = true;
    for (int s : active_stations) is_required[s] = true;

    bool changed = true;
    while(changed) {
        changed = false;
        vector<int> cur_deg(N + 1, 0);
        for(int eid : active_edge_set) {
            cur_deg[edges[eid-1].u]++;
            cur_deg[edges[eid-1].v]++;
        }
        
        for(int i = 1; i <= N; ++i) {
            if (cur_deg[i] == 1 && !is_required[i]) {
                int edge_to_remove = -1;
                for(int eid : active_edge_set) {
                    if (edges[eid-1].u == i || edges[eid-1].v == i) {
                        edge_to_remove = eid;
                        break;
                    }
                }
                if (edge_to_remove != -1) {
                    active_edge_set.erase(edge_to_remove);
                    mst_weight -= edges[edge_to_remove-1].w;
                    changed = true;
                }
            }
        }
    }

    out_edges.assign(active_edge_set.begin(), active_edge_set.end());
    fill(out_tree_nodes.begin(), out_tree_nodes.end(), false);
    out_tree_nodes[1] = true;
    for(int eid : out_edges) {
        out_tree_nodes[edges[eid-1].u] = true;
        out_tree_nodes[edges[eid-1].v] = true;
    }
    
    return mst_weight;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> N >> M >> K)) return 0;
    
    stations.resize(N + 1);
    for (int i = 1; i <= N; ++i) cin >> stations[i].x >> stations[i].y;
    
    adj.resize(N + 1);
    edges.reserve(M);
    for (int i = 1; i <= M; ++i) {
        int u, v;
        long long w;
        cin >> u >> v >> w;
        edges.push_back({u, v, w, i});
        adj[u].push_back({v, w});
        adj[v].push_back({u, w});
    }
    
    residents.resize(K);
    for (int i = 0; i < K; ++i) {
        cin >> residents[i].x >> residents[i].y;
        residents[i].id = i;
    }
    
    floyd_warshall();
    
    for (int i = 1; i <= N; ++i) {
        for (int k = 0; k < K; ++k) {
            long long d2 = dist_sq_res(i, k);
            res_to_station_req[k][i] = (int)ceil(sqrt(d2));
        }
    }
    
    assignment.resize(K);
    station_reqs.resize(N + 1);
    P.assign(N + 1, 0);
    
    for (int k = 0; k < K; ++k) {
        int best_s = -1;
        long long min_cost = INF_LL;
        for (int i = 1; i <= N; ++i) {
            long long req = res_to_station_req[k][i];
            long long p_cost = req * req;
            long long conn_cost = dist_mat[1][i]; 
            if (p_cost + conn_cost < min_cost) {
                min_cost = p_cost + conn_cost;
                best_s = i;
            }
        }
        assignment[k] = best_s;
        station_reqs[best_s].insert(res_to_station_req[k][best_s]);
    }
    
    vector<int> active_stations;
    long long power_cost = 0;
    for (int i = 1; i <= N; ++i) {
        if (!station_reqs[i].empty()) {
            P[i] = *station_reqs[i].rbegin();
            active_stations.push_back(i);
            power_cost += (long long)P[i] * P[i];
        } else {
            P[i] = 0;
        }
    }
    
    long long cable_cost = build_steiner_tree(active_stations, current_edges, tree_nodes);
    current_score = power_cost + cable_cost;
    
    auto start_time = chrono::steady_clock::now();
    double time_limit = 1.90; 
    
    int iter = 0;
    while (true) {
        iter++;
        if ((iter & 63) == 0) {
            auto curr_time = chrono::steady_clock::now();
            chrono::duration<double> diff = curr_time - start_time;
            if (diff.count() > time_limit) break;
        }
        
        int k = rng() % K;
        int old_s = assignment[k];
        
        long long old_p_sq = (long long)P[old_s] * P[old_s];
        
        int val_k = res_to_station_req[k][old_s];
        auto it = station_reqs[old_s].find(val_k);
        station_reqs[old_s].erase(it);
        
        int new_P_old_s = 0;
        if (!station_reqs[old_s].empty()) new_P_old_s = *station_reqs[old_s].rbegin();
        long long new_old_p_sq = (long long)new_P_old_s * new_P_old_s;
        
        long long gain = old_p_sq - new_old_p_sq; 
        
        int best_new_s = -1;
        long long best_delta = INF_LL; 
        
        for (int s = 1; s <= N; ++s) {
            if (s == old_s) continue;
            
            int req = res_to_station_req[k][s];
            int current_P_s = P[s];
            int new_P_s = max(current_P_s, req);
            
            long long cost_increase_power = (long long)new_P_s * new_P_s - (long long)current_P_s * current_P_s;
            long long cost_increase_conn = 0;
            
            if (current_P_s == 0 && !tree_nodes[s]) {
                long long dist_to_tree = INF_LL;
                for (int t = 1; t <= N; ++t) {
                    if (tree_nodes[t]) {
                        if (dist_mat[s][t] < dist_to_tree) dist_to_tree = dist_mat[s][t];
                    }
                }
                cost_increase_conn = dist_to_tree;
            } 
            
            long long total_delta = cost_increase_power + cost_increase_conn - gain;
            
            if (total_delta < best_delta) {
                best_delta = total_delta;
                best_new_s = s;
            }
        }
        
        if (best_delta < 0) {
            bool need_rebuild = false;
            if (new_P_old_s == 0 && old_p_sq > 0) need_rebuild = true;
            if (P[best_new_s] == 0 && res_to_station_req[k][best_new_s] > 0) need_rebuild = true;
            
            P[old_s] = new_P_old_s;
            assignment[k] = best_new_s;
            station_reqs[best_new_s].insert(res_to_station_req[k][best_new_s]);
            P[best_new_s] = *station_reqs[best_new_s].rbegin();
            
            if (iter % 200 == 0 || need_rebuild) {
               active_stations.clear();
               for(int i=1; i<=N; ++i) if(P[i] > 0) active_stations.push_back(i);
               cable_cost = build_steiner_tree(active_stations, current_edges, tree_nodes);
               power_cost = 0;
               for(int i=1; i<=N; ++i) power_cost += (long long)P[i]*P[i];
               current_score = power_cost + cable_cost;
            } 
        } else {
            station_reqs[old_s].insert(val_k);
        }
    }
    
    active_stations.clear();
    for(int i=1; i<=N; ++i) if(P[i] > 0) active_stations.push_back(i);
    build_steiner_tree(active_stations, current_edges, tree_nodes);

    for (int i = 1; i <= N; ++i) {
        cout << P[i] << (i == N ? "" : " ");
    }
    cout << "\n";
    
    vector<int> B(M + 1, 0);
    for (int eid : current_edges) B[eid] = 1;
    for (int i = 1; i <= M; ++i) {
        cout << B[i] << (i == M ? "" : " ");
    }
    cout << "\n";

    return 0;
}