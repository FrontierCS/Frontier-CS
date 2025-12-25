#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <iomanip>
#include <ctime>

using namespace std;

// Constants and Globals
const int MAXN = 105;
const int MAXM = 305;
const int MAXK = 5005;
const long long INF_LL = 1e18;

struct Edge {
    int u, v, w, id;
};

struct Resident {
    int x, y, id;
};

struct Point {
    int x, y;
};

int N, M, K;
Point stations[MAXN];
vector<Edge> edges;
vector<pair<int, int>> adj[MAXN]; // neighbor, edge_index
Resident residents[MAXK];

// Precomputed
long long graph_dist[MAXN][MAXN];
int path_next[MAXN][MAXN]; // path_next[u][v] = next node after u on path to v
int dist_sq[MAXN][MAXK]; // distance squared from station i to resident k
vector<int> sorted_stations[MAXK]; // stations sorted by dist to resident k

// State
bool is_active[MAXN];

// Random
unsigned int rng_state = 12345;
int my_rand() {
    rng_state = rng_state * 1664525 + 1013904223;
    return (rng_state >> 16) & 32767;
}

// Distance calc
int get_dist_sq(int u, int k) {
    long long dx = stations[u].x - residents[k].x;
    long long dy = stations[u].y - residents[k].y;
    long long d2 = dx*dx + dy*dy;
    if (d2 > 2000000000LL) return 2000000000; // Cap to avoid overflow if needed, though coordinates are 10^4
    return (int)d2;
}

// Precompute Shortest Paths (Floyd-Warshall)
void precompute_paths() {
    for(int i=1; i<=N; ++i) {
        for(int j=1; j<=N; ++j) {
            if (i == j) graph_dist[i][j] = 0;
            else graph_dist[i][j] = INF_LL;
            path_next[i][j] = -1;
        }
    }
    for(const auto& e : edges) {
        if (e.w < graph_dist[e.u][e.v]) {
            graph_dist[e.u][e.v] = e.w;
            graph_dist[e.v][e.u] = e.w;
            path_next[e.u][e.v] = e.v;
            path_next[e.v][e.u] = e.u;
        }
    }

    for(int k=1; k<=N; ++k) {
        for(int i=1; i<=N; ++i) {
            for(int j=1; j<=N; ++j) {
                if (graph_dist[i][k] != INF_LL && graph_dist[k][j] != INF_LL) {
                    if (graph_dist[i][k] + graph_dist[k][j] < graph_dist[i][j]) {
                        graph_dist[i][j] = graph_dist[i][k] + graph_dist[k][j];
                        path_next[i][j] = path_next[i][k];
                    }
                }
            }
        }
    }
}

// Evaluate State
pair<long long, vector<int>> evaluate(const bool current_active[MAXN]) {
    long long broadcast_cost = 0;
    static int current_P[MAXN];
    for(int i=1; i<=N; ++i) current_P[i] = 0;

    for(int k=0; k<K; ++k) {
        int best_u = -1;
        for(int u : sorted_stations[k]) {
            if(current_active[u]) {
                best_u = u;
                break;
            }
        }
        if (best_u == -1) return {INF_LL, {}};

        int d2 = dist_sq[best_u][k];
        int req_P = sqrt(d2);
        if(req_P * req_P < d2) req_P++;
        
        if(req_P > 5000) return {INF_LL, {}}; // Constraint violation
        
        if(req_P > current_P[best_u]) current_P[best_u] = req_P;
    }

    for(int i=1; i<=N; ++i) {
        if(current_active[i]) {
            broadcast_cost += (long long)current_P[i] * current_P[i];
        }
    }

    vector<int> nodes_to_connect;
    nodes_to_connect.push_back(1);
    for(int i=2; i<=N; ++i) {
        if(current_active[i] && current_P[i] > 0) {
            nodes_to_connect.push_back(i);
        }
    }
    
    long long network_cost = 0;
    vector<int> used_edges; 
    
    static bool edge_status[MAXM + 1];
    for(int i=1; i<=M; ++i) edge_status[i] = false;

    static bool in_tree[MAXN + 1];
    for(int i=1; i<=N; ++i) in_tree[i] = false;
    
    static long long min_dist[MAXN + 1];
    static int closest_in_tree[MAXN + 1];

    in_tree[1] = true;
    for(int i=1; i<=N; ++i) {
        min_dist[i] = graph_dist[1][i];
        closest_in_tree[i] = 1;
    }

    static bool is_target[MAXN + 1];
    for(int i=1; i<=N; ++i) is_target[i] = false;
    int target_count = 0;
    for(int u : nodes_to_connect) {
        is_target[u] = true;
        if(u != 1) target_count++;
    }
    
    int connected_targets = 0;
    
    while(connected_targets < target_count) {
        int best_u = -1;
        long long best_d = INF_LL;

        for(int i=1; i<=N; ++i) {
            if(is_target[i] && !in_tree[i]) {
                if(min_dist[i] < best_d) {
                    best_d = min_dist[i];
                    best_u = i;
                }
            }
        }

        if(best_u == -1) break; 

        int curr = closest_in_tree[best_u];
        int target = best_u;
        
        int u = curr;
        while(u != target) {
            int v = path_next[u][target];
            
            int best_eid = -1;
            int min_w = 2100000000;
            for(auto& p : adj[u]) {
                if(p.first == v) {
                    // Among multiple edges, pick the one consistent with shortest path weight
                    // Though path_next comes from min weight edges
                    if (edges[p.second-1].w < min_w) {
                        min_w = edges[p.second-1].w;
                        best_eid = p.second;
                    }
                }
            }
            
            if(!edge_status[best_eid]) {
                edge_status[best_eid] = true;
                network_cost += edges[best_eid-1].w;
                used_edges.push_back(best_eid);
            }

            if(!in_tree[v]) {
                in_tree[v] = true;
                if(is_target[v]) connected_targets++;
                for(int k=1; k<=N; ++k) {
                    if(!in_tree[k]) {
                        if(graph_dist[v][k] < min_dist[k]) {
                            min_dist[k] = graph_dist[v][k];
                            closest_in_tree[k] = v;
                        }
                    }
                }
            }
            u = v;
        }
    }
    
    return {broadcast_cost + network_cost, used_edges};
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> N >> M >> K;
    for(int i=1; i<=N; ++i) cin >> stations[i].x >> stations[i].y;
    for(int i=1; i<=M; ++i) {
        int u, v, w;
        cin >> u >> v >> w;
        edges.push_back({u, v, w, i});
        adj[u].push_back({v, i});
        adj[v].push_back({u, i});
    }
    for(int i=0; i<K; ++i) {
        cin >> residents[i].x >> residents[i].y;
        residents[i].id = i;
    }

    precompute_paths();
    for(int k=0; k<K; ++k) {
        for(int i=1; i<=N; ++i) {
            dist_sq[i][k] = get_dist_sq(i, k);
            sorted_stations[k].push_back(i);
        }
        sort(sorted_stations[k].begin(), sorted_stations[k].end(), [&](int a, int b){
            return dist_sq[a][k] < dist_sq[b][k];
        });
    }

    // Initial Solution: All Active
    for(int i=1; i<=N; ++i) is_active[i] = true;
    
    pair<long long, vector<int>> best_res = evaluate(is_active);
    long long best_cost = best_res.first;
    bool best_active[MAXN];
    for(int i=1; i<=N; ++i) best_active[i] = true;

    // Optimization Loop
    double time_limit = 1.9;
    clock_t start_time = clock();
    
    long long current_cost = best_cost;
    int iter = 0;
    
    while((double)(clock() - start_time) / CLOCKS_PER_SEC < time_limit) {
        iter++;
        int u = (my_rand() % (N - 1)) + 2; // 2 to N
        
        is_active[u] = !is_active[u];
        
        pair<long long, vector<int>> attempt = evaluate(is_active);
        long long new_cost = attempt.first;
        
        if(new_cost < current_cost) {
            current_cost = new_cost;
            if(new_cost < best_cost) {
                best_cost = new_cost;
                for(int i=1; i<=N; ++i) best_active[i] = is_active[i];
            }
        } else {
            is_active[u] = !is_active[u]; // Revert
        }
        
        // Perturbation
        if (iter % 1500 == 0) {
             int num_flip = my_rand() % 3 + 1;
             vector<int> flipped;
             for(int k=0; k<num_flip; ++k) {
                 int v = (my_rand() % (N - 1)) + 2;
                 is_active[v] = !is_active[v];
                 flipped.push_back(v);
             }
             pair<long long, vector<int>> att = evaluate(is_active);
             if(att.first < best_cost) {
                 best_cost = att.first;
                 current_cost = att.first;
                 for(int i=1; i<=N; ++i) best_active[i] = is_active[i];
             } else {
                 if(att.first < current_cost * 1.05) { // Accept slight degradation
                     current_cost = att.first;
                 } else {
                     for(int v : flipped) is_active[v] = !is_active[v]; // Revert
                 }
             }
        }
    }

    pair<long long, vector<int>> final_res = evaluate(best_active);
    
    int final_P[MAXN];
    for(int i=1; i<=N; ++i) final_P[i] = 0;
    for(int k=0; k<K; ++k) {
        int best_u = -1;
        for(int u : sorted_stations[k]) {
            if(best_active[u]) {
                best_u = u;
                break;
            }
        }
        int d2 = dist_sq[best_u][k];
        int req_P = sqrt(d2);
        if(req_P * req_P < d2) req_P++;
        if(req_P > final_P[best_u]) final_P[best_u] = req_P;
    }
    
    for(int i=1; i<=N; ++i) {
        cout << final_P[i] << (i==N ? "" : " ");
    }
    cout << "\n";

    vector<int> B(M + 1, 0);
    for(int eid : final_res.second) {
        B[eid] = 1;
    }
    for(int i=1; i<=M; ++i) {
        cout << B[i] << (i==M ? "" : " ");
    }
    cout << "\n";

    return 0;
}