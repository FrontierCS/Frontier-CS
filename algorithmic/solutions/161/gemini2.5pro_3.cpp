#include <iostream>
#include <vector>
#include <cmath>
#include <numeric>
#include <algorithm>
#include <queue>
#include <functional>

using namespace std;

// Using long long for coordinates to be safe with intermediate products
struct Point {
    long long x, y;
};

struct Edge {
    int u, v, w, id;
};

const long long INF_LL = 1e18;
const int N_MAX = 101, M_MAX = 301, K_MAX = 5001;

int N, M, K;
Point stations[N_MAX];
Edge edges[M_MAX];
Point residents[K_MAX];

vector<pair<int, int>> adj[N_MAX];
long long dist_G[N_MAX][N_MAX];
int parent_G[N_MAX][N_MAX];
int station_resident_dist[N_MAX][K_MAX];

long long dist_sq(Point p1, Point p2) {
    return (p1.x - p2.x) * (p1.x - p2.x) + (p1.y - p2.y) * (p1.y - p2.y);
}

void dijkstra(int start_node) {
    for (int i = 1; i <= N; ++i) {
        dist_G[start_node][i] = INF_LL;
        parent_G[start_node][i] = 0;
    }
    dist_G[start_node][start_node] = 0;
    priority_queue<pair<long long, int>, vector<pair<long long, int>>, greater<pair<long long, int>>> pq;
    pq.push({0, start_node});

    while (!pq.empty()) {
        auto [d, u] = pq.top();
        pq.pop();

        if (d > dist_G[start_node][u]) {
            continue;
        }

        for (auto& edge_info : adj[u]) {
            int v = edge_info.first;
            int edge_idx = edge_info.second;
            long long w = edges[edge_idx].w;
            if (dist_G[start_node][u] + w < dist_G[start_node][v]) {
                dist_G[start_node][v] = dist_G[start_node][u] + w;
                parent_G[start_node][v] = u;
                pq.push({dist_G[start_node][v], v});
            }
        }
    }
}

pair<long long, vector<int>> get_refined_coverage(const vector<int>& active_stations_vec) {
    vector<int> P(N + 1, 0);
    if (active_stations_vec.empty()) return {0, P};

    vector<int> resident_assignment(K);
    vector<vector<int>> station_covers(N + 1);

    for (int k = 0; k < K; ++k) {
        long long best_dist_sq = -1;
        int best_station = -1;
        for (int s_idx : active_stations_vec) {
            long long d_sq = dist_sq(stations[s_idx], residents[k]);
            if (best_station == -1 || d_sq < best_dist_sq) {
                best_dist_sq = d_sq;
                best_station = s_idx;
            }
        }
        resident_assignment[k] = best_station;
        station_covers[best_station].push_back(k);
    }
    
    for (int s_idx : active_stations_vec) {
        for(int res_idx : station_covers[s_idx]) {
            P[s_idx] = max(P[s_idx], station_resident_dist[s_idx][res_idx]);
        }
    }

    for (int iter = 0; iter < 2; ++iter) {
        for (int k = 0; k < K; ++k) {
            int current_station = resident_assignment[k];
            
            long long old_P_current_sq = (long long)P[current_station] * P[current_station];
            int new_P_current_val = 0;
            for(int res_idx : station_covers[current_station]) {
                if(res_idx == k) continue;
                new_P_current_val = max(new_P_current_val, station_resident_dist[current_station][res_idx]);
            }
            long long new_P_current_sq = (long long)new_P_current_val * new_P_current_val;
            
            int best_new_station = current_station;
            long long min_total_cost_change = 0;

            for (int s_idx : active_stations_vec) {
                if (s_idx == current_station) continue;

                long long old_P_s_sq = (long long)P[s_idx] * P[s_idx];
                int new_P_s_val = max(P[s_idx], station_resident_dist[s_idx][k]);
                long long new_P_s_sq = (long long)new_P_s_val * new_P_s_val;

                long long cost_change = (new_P_current_sq - old_P_current_sq) + (new_P_s_sq - old_P_s_sq);

                if (cost_change < min_total_cost_change) {
                    min_total_cost_change = cost_change;
                    best_new_station = s_idx;
                }
            }

            if (best_new_station != current_station) {
                auto& prev_covers = station_covers[current_station];
                prev_covers.erase(remove(prev_covers.begin(), prev_covers.end(), k), prev_covers.end());
                station_covers[best_new_station].push_back(k);
                resident_assignment[k] = best_new_station;

                P[current_station] = new_P_current_val;
                P[best_new_station] = max(P[best_new_station], station_resident_dist[best_new_station][k]);
            }
        }
    }

    long long total_coverage_cost = 0;
    fill(P.begin(), P.end(), 0);
    for (int s_idx : active_stations_vec) {
        for (int res_idx : station_covers[s_idx]) {
            P[s_idx] = max(P[s_idx], station_resident_dist[s_idx][res_idx]);
        }
        total_coverage_cost += (long long)P[s_idx] * P[s_idx];
    }
    
    return {total_coverage_cost, P};
}

long long get_connection_cost(const vector<int>& active_stations_vec) {
    if (active_stations_vec.size() <= 1) return 0;
    
    long long total_w = 0;
    vector<long long> min_cost(N + 1, INF_LL);
    vector<bool> in_tree(N + 1, false);
    
    min_cost[active_stations_vec[0]] = 0;
    
    for (size_t i = 0; i < active_stations_vec.size(); ++i) {
        int u = -1;
        for (int station_idx : active_stations_vec) {
            if (!in_tree[station_idx] && (u == -1 || min_cost[station_idx] < min_cost[u])) {
                u = station_idx;
            }
        }
        if (u == -1) break;
        in_tree[u] = true;
        total_w += min_cost[u];

        for (int v : active_stations_vec) {
            if (!in_tree[v] && dist_G[u][v] < min_cost[v]) {
                min_cost[v] = dist_G[u][v];
            }
        }
    }
    return total_w;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> N >> M >> K;
    for (int i = 1; i <= N; ++i) cin >> stations[i].x >> stations[i].y;
    for (int i = 0; i < M; ++i) {
        cin >> edges[i].u >> edges[i].v >> edges[i].w;
        edges[i].id = i;
        adj[edges[i].u].push_back({edges[i].v, i});
        adj[edges[i].v].push_back({edges[i].u, i});
    }
    for (int i = 0; i < K; ++i) cin >> residents[i].x >> residents[i].y;

    for (int i = 1; i <= N; ++i) dijkstra(i);
    for(int i = 1; i <= N; ++i) {
        for(int k = 0; k < K; ++k) {
            station_resident_dist[i][k] = ceil(sqrt(dist_sq(stations[i], residents[k])));
        }
    }

    vector<bool> is_active(N + 1, false);
    is_active[1] = true;
    
    // Greedy forward selection
    for (int iter = 0; iter < N - 1; ++iter) {
        long long current_best_total_cost;
        int station_to_add = -1;
        
        vector<int> current_active;
        for(int i=1; i<=N; ++i) if(is_active[i]) current_active.push_back(i);
        current_best_total_cost = get_connection_cost(current_active) + get_refined_coverage(current_active).first;

        for (int i = 2; i <= N; ++i) {
            if (is_active[i]) continue;
            vector<int> next_active = current_active;
            next_active.push_back(i);
            long long next_total_cost = get_connection_cost(next_active) + get_refined_coverage(next_active).first;
            if (next_total_cost < current_best_total_cost) {
                current_best_total_cost = next_total_cost;
                station_to_add = i;
            }
        }
        
        if (station_to_add != -1) {
            is_active[station_to_add] = true;
        } else {
            break;
        }
    }

    // Local search (hill climbing)
    bool changed_in_pass = true;
    while(changed_in_pass) {
        changed_in_pass = false;
        vector<int> current_active;
        for(int i=1; i<=N; ++i) if(is_active[i]) current_active.push_back(i);
        long long best_cost = get_connection_cost(current_active) + get_refined_coverage(current_active).first;
        
        // Try removing a station
        int station_to_remove = -1;
        for(int s_idx : current_active) {
            if(s_idx == 1) continue;
            vector<int> next_active;
            for(int s : current_active) if(s != s_idx) next_active.push_back(s);
            long long next_cost = get_connection_cost(next_active) + get_refined_coverage(next_active).first;
            if (next_cost < best_cost) {
                best_cost = next_cost;
                station_to_remove = s_idx;
            }
        }
        if(station_to_remove != -1) {
            is_active[station_to_remove] = false;
            changed_in_pass = true;
            continue;
        }

        // Try adding a station
        int station_to_add = -1;
        for(int i=2; i<=N; ++i) {
            if(is_active[i]) continue;
            vector<int> next_active = current_active;
            next_active.push_back(i);
            long long next_cost = get_connection_cost(next_active) + get_refined_coverage(next_active).first;
            if (next_cost < best_cost) {
                best_cost = next_cost;
                station_to_add = i;
            }
        }
        if(station_to_add != -1) {
            is_active[station_to_add] = true;
            changed_in_pass = true;
        }
    }

    vector<int> final_active_stations;
    for (int i = 1; i <= N; ++i) if (is_active[i]) final_active_stations.push_back(i);

    auto [final_coverage_cost, final_P] = get_refined_coverage(final_active_stations);

    vector<int> B(M, 0);
    if (final_active_stations.size() > 1) {
        vector<pair<long long, pair<int, int>>> steiner_edges;
        for (size_t i = 0; i < final_active_stations.size(); ++i) {
            for (size_t j = i + 1; j < final_active_stations.size(); ++j) {
                int u = final_active_stations[i];
                int v = final_active_stations[j];
                steiner_edges.push_back({dist_G[u][v], {u, v}});
            }
        }
        sort(steiner_edges.begin(), steiner_edges.end());

        vector<int> dsu_parent(N + 1);
        iota(dsu_parent.begin(), dsu_parent.end(), 0);
        function<int(int)> find_set = [&](int v) {
            return (v == dsu_parent[v]) ? v : dsu_parent[v] = find_set(dsu_parent[v]);
        };
        auto unite_sets = [&](int a, int b) {
            a = find_set(a); b = find_set(b);
            if (a != b) dsu_parent[b] = a;
        };

        for (const auto& edge : steiner_edges) {
            int u = edge.second.first, v = edge.second.second;
            if (find_set(u) != find_set(v)) {
                unite_sets(u, v);
                int curr = v;
                while (curr != u && curr != 0) {
                    int p = parent_G[u][curr];
                    bool found = false;
                    for (const auto& adj_edge : adj[curr]) {
                        if (adj_edge.first == p) {
                            B[adj_edge.second] = 1;
                            found = true;
                            break;
                        }
                    }
                    if(!found) break; // Should not happen in a connected graph
                    curr = p;
                }
            }
        }
    }
    
    for (int i = 1; i <= N; ++i) cout << final_P[i] << (i == N ? "" : " ");
    cout << endl;
    for (int i = 0; i < M; ++i) cout << B[i] << (i == M - 1 ? "" : " ");
    cout << endl;

    return 0;
}