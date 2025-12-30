#include <iostream>
#include <vector>
#include <cmath>
#include <queue>
#include <map>
#include <algorithm>
#include <tuple>

using namespace std;

const long long INF = 1e18;

struct Point {
    long long x, y;
};

struct Edge {
    int to;
    int weight;
    int id;
};

struct State {
    long long cost;
    int u;

    bool operator>(const State& other) const {
        return cost > other.cost;
    }
};

int N, M, K;
vector<Point> stations;
vector<Point> residents;
vector<vector<Edge>> adj;

vector<vector<long long>> path_cost;
vector<vector<int>> path_pred_v;

void dijkstra(int start_node) {
    path_cost[start_node].assign(N + 1, INF);
    path_pred_v[start_node].assign(N + 1, 0);
    path_cost[start_node][start_node] = 0;
    priority_queue<State, vector<State>, greater<State>> pq;
    pq.push({0, start_node});

    while (!pq.empty()) {
        auto [cost, u] = pq.top();
        pq.pop();

        if (cost > path_cost[start_node][u]) {
            continue;
        }

        for (const auto& edge : adj[u]) {
            if (path_cost[start_node][u] + edge.weight < path_cost[start_node][edge.to]) {
                path_cost[start_node][edge.to] = path_cost[start_node][u] + edge.weight;
                path_pred_v[start_node][edge.to] = u;
                pq.push({path_cost[start_node][edge.to], edge.to});
            }
        }
    }
}

long long dist_sq(const Point& p1, const Point& p2) {
    return (p1.x - p2.x) * (p1.x - p2.x) + (p1.y - p2.y) * (p1.y - p2.y);
}

long long calculate_power_cost(const vector<int>& V_p, const vector<int>& assignments, const vector<long long>& current_min_dists) {
    if (V_p.empty()) return 0;
    vector<double> max_dist(N + 1, 0.0);
    for (int k = 0; k < K; ++k) {
        int s = assignments[k];
        max_dist[s] = max(max_dist[s], sqrt((double)current_min_dists[k]));
    }
    long long total_power_cost = 0;
    for (int s : V_p) {
        long long p = ceil(max_dist[s]);
        total_power_cost += p * p;
    }
    return total_power_cost;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> N >> M >> K;
    stations.resize(N + 1);
    residents.resize(K);
    adj.resize(N + 1);

    for (int i = 1; i <= N; ++i) {
        cin >> stations[i].x >> stations[i].y;
    }
    for (int i = 1; i <= M; ++i) {
        int u, v, w;
        cin >> u >> v >> w;
        adj[u].push_back({v, w, i});
        adj[v].push_back({u, w, i});
    }
    for (int i = 0; i < K; ++i) {
        cin >> residents[i].x >> residents[i].y;
    }

    path_cost.resize(N + 1);
    path_pred_v.resize(N + 1);
    for (int i = 1; i <= N; ++i) {
        dijkstra(i);
    }

    vector<vector<long long>> dist_sq_rk(K, vector<long long>(N + 1));
    for (int k = 0; k < K; ++k) {
        for (int i = 1; i <= N; ++i) {
            dist_sq_rk[k][i] = dist_sq(residents[k], stations[i]);
        }
    }

    vector<bool> active_stations(N + 1, false);
    active_stations[1] = true;
    vector<int> V_prime;
    V_prime.push_back(1);
    
    vector<pair<int, int>> mst_edges;
    
    vector<int> assigned_station(K);
    vector<long long> min_dist_sq(K);
    for (int k = 0; k < K; ++k) {
        assigned_station[k] = 1;
        min_dist_sq[k] = dist_sq_rk[k][1];
    }
    
    long long current_conn_cost = 0;
    long long current_power_cost = calculate_power_cost(V_prime, assigned_station, min_dist_sq);
    long long current_total_cost = current_conn_cost + current_power_cost;

    while (true) {
        long long best_total_cost = current_total_cost;
        int j_to_add = -1;
        int p_for_j = -1;
        vector<int> best_temp_assigned_station;
        vector<long long> best_temp_min_dist_sq;

        for (int j = 1; j <= N; ++j) {
            if (active_stations[j]) continue;

            long long conn_cost_increase = INF;
            int p_conn = -1;
            for (int i : V_prime) {
                if (path_cost[i][j] < conn_cost_increase) {
                    conn_cost_increase = path_cost[i][j];
                    p_conn = i;
                }
            }
            
            long long temp_conn_cost = current_conn_cost + conn_cost_increase;

            vector<int> temp_assigned_station = assigned_station;
            vector<long long> temp_min_dist_sq = min_dist_sq;
            vector<int> temp_V_prime = V_prime;
            temp_V_prime.push_back(j);

            for (int k = 0; k < K; ++k) {
                if (dist_sq_rk[k][j] < temp_min_dist_sq[k]) {
                    temp_assigned_station[k] = j;
                    temp_min_dist_sq[k] = dist_sq_rk[k][j];
                }
            }
            
            long long temp_power_cost = calculate_power_cost(temp_V_prime, temp_assigned_station, temp_min_dist_sq);
            long long temp_total_cost = temp_conn_cost + temp_power_cost;

            if (temp_total_cost < best_total_cost) {
                best_total_cost = temp_total_cost;
                j_to_add = j;
                p_for_j = p_conn;
                best_temp_assigned_station = temp_assigned_station;
                best_temp_min_dist_sq = temp_min_dist_sq;
            }
        }

        if (j_to_add != -1) {
            active_stations[j_to_add] = true;
            V_prime.push_back(j_to_add);
            mst_edges.push_back({j_to_add, p_for_j});
            current_conn_cost += path_cost[j_to_add][p_for_j];
            assigned_station = best_temp_assigned_station;
            min_dist_sq = best_temp_min_dist_sq;
            current_total_cost = best_total_cost;
        } else {
            break;
        }
    }

    vector<vector<int>> residents_per_station(N + 1);
    for(int k=0; k<K; ++k) residents_per_station[assigned_station[k]].push_back(k);

    vector<double> station_max_dist_sqrt(N+1, 0.0);
    for(int s : V_prime) {
        if(!residents_per_station[s].empty()) {
            double max_d2 = 0;
            for(int res_idx : residents_per_station[s]) {
                max_d2 = max(max_d2, (double)dist_sq_rk[res_idx][s]);
            }
            station_max_dist_sqrt[s] = sqrt(max_d2);
        }
    }

    for(int iter = 0; iter < 2; ++iter) {
        bool changed_in_iter = false;
        for (int k = 0; k < K; ++k) {
            int s_old = assigned_station[k];
            long long current_cost_s_old = (long long)ceil(station_max_dist_sqrt[s_old]) * (long long)ceil(station_max_dist_sqrt[s_old]);

            long long best_cost_change = 0;
            int best_s_new = -1;

            for (int s_new : V_prime) {
                if (s_new == s_old) continue;
                
                long long current_cost_s_new = (long long)ceil(station_max_dist_sqrt[s_new]) * (long long)ceil(station_max_dist_sqrt[s_new]);

                double new_dist_sqrt_s_new = max(station_max_dist_sqrt[s_new], sqrt((double)dist_sq_rk[k][s_new]));
                long long new_cost_s_new = (long long)ceil(new_dist_sqrt_s_new) * (long long)ceil(new_dist_sqrt_s_new);
                
                double new_dist_sqrt_s_old = 0;
                if(abs(station_max_dist_sqrt[s_old] - sqrt((double)dist_sq_rk[k][s_old])) < 1e-9) {
                    double max_d2 = 0;
                    for(int other_k : residents_per_station[s_old]) {
                        if (other_k == k) continue;
                        max_d2 = max(max_d2, (double)dist_sq_rk[other_k][s_old]);
                    }
                    if (max_d2 > 0) new_dist_sqrt_s_old = sqrt(max_d2);
                } else {
                    new_dist_sqrt_s_old = station_max_dist_sqrt[s_old];
                }
                long long new_cost_s_old = (long long)ceil(new_dist_sqrt_s_old) * (long long)ceil(new_dist_sqrt_s_old);

                long long cost_change = (new_cost_s_old + new_cost_s_new) - (current_cost_s_old + current_cost_s_new);
                if (cost_change < best_cost_change) {
                    best_cost_change = cost_change;
                    best_s_new = s_new;
                }
            }
            
            if (best_s_new != -1) {
                changed_in_iter = true;
                int s_new = best_s_new;
                
                station_max_dist_sqrt[s_new] = max(station_max_dist_sqrt[s_new], sqrt((double)dist_sq_rk[k][s_new]));
                if(abs(station_max_dist_sqrt[s_old] - sqrt((double)dist_sq_rk[k][s_old])) < 1e-9) {
                    double max_d2 = 0;
                    for(int other_k : residents_per_station[s_old]) {
                        if (other_k == k) continue;
                        max_d2 = max(max_d2, (double)dist_sq_rk[other_k][s_old]);
                    }
                    station_max_dist_sqrt[s_old] = (max_d2 > 0) ? sqrt(max_d2) : 0;
                }

                assigned_station[k] = s_new;
                auto& s_old_res = residents_per_station[s_old];
                s_old_res.erase(remove(s_old_res.begin(), s_old_res.end(), k), s_old_res.end());
                residents_per_station[s_new].push_back(k);
            }
        }
        if(!changed_in_iter) break;
    }


    vector<int> P(N + 1, 0);
    for(int s : V_prime){
        P[s] = ceil(station_max_dist_sqrt[s]);
    }
    
    vector<bool> B(M + 1, false);
    for (const auto& edge : mst_edges) {
        int u = edge.first;
        int v = edge.second;
        int curr = u;
        while (curr != v) {
            int prev = path_pred_v[v][curr];
            for (const auto& e : adj[curr]) {
                if (e.to == prev && path_cost[v][curr] == path_cost[v][prev] + e.weight) {
                    B[e.id] = true;
                    break;
                }
            }
            curr = prev;
        }
    }

    for (int i = 1; i <= N; ++i) {
        cout << P[i] << (i == N ? "" : " ");
    }
    cout << endl;
    for (int i = 1; i <= M; ++i) {
        cout << B[i] << (i == M ? "" : " ");
    }
    cout << endl;

    return 0;
}