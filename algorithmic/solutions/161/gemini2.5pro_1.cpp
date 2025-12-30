#include <iostream>
#include <vector>
#include <cmath>
#include <numeric>
#include <algorithm>
#include <random>
#include <chrono>
#include <tuple>
#include <queue>

using namespace std;

const long long INF = 1e18;

struct Point {
    long long x, y;
};

long long dist_sq(Point p1, Point p2) {
    return (p1.x - p2.x) * (p1.x - p2.x) + (p1.y - p2.y) * (p1.y - p2.y);
}

int N, M, K;
vector<Point> stations;
vector<tuple<int, int, int>> edges;
vector<Point> residents;

vector<vector<pair<int, int>>> adj;
vector<vector<long long>> dist_matrix;
vector<vector<int>> parent_matrix;

vector<vector<int>> resident_station_dists;
vector<vector<int>> closest_stations;

auto start_time = chrono::high_resolution_clock::now();
mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

double time_elapsed() {
    auto now = chrono::high_resolution_clock::now();
    return chrono::duration<double>(now - start_time).count();
}

void dijkstra(int start_node) {
    dist_matrix[start_node].assign(N + 1, INF);
    parent_matrix[start_node].assign(N + 1, 0);
    dist_matrix[start_node][start_node] = 0;

    priority_queue<pair<long long, int>, vector<pair<long long, int>>, greater<pair<long long, int>>> pq;
    pq.push({0, start_node});

    while (!pq.empty()) {
        auto [d, u] = pq.top();
        pq.pop();

        if (d > dist_matrix[start_node][u]) {
            continue;
        }

        for (auto& edge : adj[u]) {
            int v = edge.first;
            int weight = edge.second;
            if (dist_matrix[start_node][u] + weight < dist_matrix[start_node][v]) {
                dist_matrix[start_node][v] = dist_matrix[start_node][u] + weight;
                parent_matrix[start_node][v] = u;
                pq.push({dist_matrix[start_node][v], v});
            }
        }
    }
}

void calculate_final_edges(const vector<int>& p, vector<int>& b_out) {
    vector<int> Vp;
    for (int i = 1; i <= N; ++i) {
        if (p[i] > 0) {
            Vp.push_back(i);
        }
    }
    if (Vp.empty()) {
        return;
    }
    
    bool has_one = false;
    for (int v : Vp) {
        if (v == 1) {
            has_one = true;
            break;
        }
    }
    if (!has_one) {
        Vp.push_back(1);
    }
    
    if (Vp.size() <= 1) {
        return;
    }

    vector<pair<int, int>> mst_edges;
    
    vector<long long> min_cost(N + 1, INF);
    vector<int> edge_to(N + 1, -1);
    vector<bool> in_mst(N + 1, false);
    
    min_cost[1] = 0;
    
    for (size_t i = 0; i < Vp.size(); ++i) {
        int u = -1;
        for (int v : Vp) {
            if (!in_mst[v] && (u == -1 || min_cost[v] < min_cost[u])) {
                u = v;
            }
        }
        if (u == -1) break;

        in_mst[u] = true;
        if (edge_to[u] != -1) {
            mst_edges.push_back({u, edge_to[u]});
        }

        for (int v : Vp) {
            if (!in_mst[v]) {
                if (dist_matrix[u][v] < min_cost[v]) {
                    min_cost[v] = dist_matrix[u][v];
                    edge_to[v] = u;
                }
            }
        }
    }

    vector<vector<int>> edge_map(N + 1, vector<int>(N + 1, 0));
    for (int i = 0; i < M; ++i) {
        auto [u, v, w] = edges[i];
        edge_map[u][v] = edge_map[v][u] = i + 1;
    }

    for (const auto& edge : mst_edges) {
        int u = edge.first;
        int v = edge.second;
        int curr = u;
        while(curr != v) {
            int p = parent_matrix[v][curr];
            int edge_idx = edge_map[curr][p];
            if (edge_idx > 0) {
                b_out[edge_idx-1] = 1;
            }
            curr = p;
        }
    }
}

struct Solution {
    vector<int> assignment;
    vector<int> p;
    long long conn_cost;
    long long broadcast_cost;
    long long total_cost;

    Solution() : assignment(K), p(N + 1, 0), conn_cost(0), broadcast_cost(0), total_cost(INF) {}

    void calculate_costs() {
        fill(p.begin(), p.end(), 0);
        for (int k = 0; k < K; ++k) {
            p[assignment[k]] = max(p[assignment[k]], resident_station_dists[k][assignment[k]]);
        }

        vector<int> Vp;
        for (int i = 1; i <= N; ++i) {
            if (p[i] > 0) {
                Vp.push_back(i);
            }
        }

        broadcast_cost = 0;
        for (int i = 1; i <= N; ++i) {
            broadcast_cost += (long long)p[i] * p[i];
        }

        if (Vp.empty()) {
            conn_cost = 0;
            total_cost = broadcast_cost;
            return;
        }

        bool has_one = false;
        for (int v : Vp) if (v == 1) has_one = true;
        if (!has_one) Vp.push_back(1);
        
        if (Vp.size() <= 1) {
            conn_cost = 0;
            total_cost = broadcast_cost;
            return;
        }

        conn_cost = 0;
        vector<long long> min_cost(N + 1, INF);
        vector<bool> in_mst(N + 1, false);
        min_cost[1] = 0;

        for (size_t i = 0; i < Vp.size(); ++i) {
            int u = -1;
            for (int v : Vp) {
                if (!in_mst[v] && (u == -1 || min_cost[v] < min_cost[u])) {
                    u = v;
                }
            }
            if (u == -1) break;
            
            in_mst[u] = true;
            conn_cost += min_cost[u];

            for (int v : Vp) {
                if (!in_mst[v]) {
                    min_cost[v] = min(min_cost[v], dist_matrix[u][v]);
                }
            }
        }
        total_cost = broadcast_cost + conn_cost;
    }
};

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> N >> M >> K;

    stations.resize(N + 1);
    for (int i = 1; i <= N; ++i) {
        cin >> stations[i].x >> stations[i].y;
    }

    edges.resize(M);
    adj.resize(N + 1);
    for (int i = 0; i < M; ++i) {
        int u, v, w;
        cin >> u >> v >> w;
        edges[i] = {u, v, w};
        adj[u].push_back({v, w});
        adj[v].push_back({u, w});
    }

    residents.resize(K);
    for (int i = 0; i < K; ++i) {
        cin >> residents[i].x >> residents[i].y;
    }

    dist_matrix.resize(N + 1);
    parent_matrix.resize(N + 1);
    for (int i = 1; i <= N; ++i) {
        dijkstra(i);
    }
    
    resident_station_dists.resize(K, vector<int>(N + 1));
    for (int k = 0; k < K; ++k) {
        for (int i = 1; i <= N; ++i) {
            resident_station_dists[k][i] = ceil(sqrt(dist_sq(residents[k], stations[i])));
        }
    }

    closest_stations.resize(K);
    for (int k = 0; k < K; ++k) {
        vector<pair<int, int>> sorted_stations(N);
        for (int i = 0; i < N; ++i) {
            sorted_stations[i] = {resident_station_dists[k][i + 1], i + 1};
        }
        sort(sorted_stations.begin(), sorted_stations.end());
        for (int i = 0; i < N; ++i) {
            closest_stations[k].push_back(sorted_stations[i].second);
        }
    }

    Solution best_sol;
    best_sol.assignment.resize(K);

    vector<long long> station_p(N + 1, 0);
    vector<bool> station_active(N + 1, false);
    station_active[1] = true;
    vector<long long> min_dist_to_active = dist_matrix[1];

    for (int k = 0; k < K; ++k) {
        int best_station = -1;
        long long min_cost_increase = -1;

        for (int i = 1; i <= N; ++i) {
            long long cost_increase = 0;
            long long new_p = max((long long)resident_station_dists[k][i], station_p[i]);
            cost_increase += new_p * new_p - station_p[i] * station_p[i];
            if (!station_active[i]) {
                cost_increase += min_dist_to_active[i];
            }

            if (best_station == -1 || cost_increase < min_cost_increase) {
                min_cost_increase = cost_increase;
                best_station = i;
            }
        }
        best_sol.assignment[k] = best_station;
        station_p[best_station] = max(station_p[best_station], (long long)resident_station_dists[k][best_station]);
        
        if (!station_active[best_station]) {
            station_active[best_station] = true;
            for(int i = 1; i <= N; ++i) {
                min_dist_to_active[i] = min(min_dist_to_active[i], dist_matrix[i][best_station]);
            }
        }
    }
    best_sol.calculate_costs();

    Solution current_sol = best_sol;

    double T_start = 5e6;
    double T_end = 1e2;
    double time_limit = 2.8;
    
    uniform_int_distribution<> k_dist(0, K - 1);
    uniform_int_distribution<> c_dist(0, min((int)N, 10) - 1);
    uniform_real_distribution<> u_dist(0.0, 1.0);

    while (time_elapsed() < time_limit) {
        double T = T_start * pow(T_end / T_start, time_elapsed() / time_limit);
        
        int k = k_dist(rng);
        int current_station = current_sol.assignment[k];
        
        int new_station_idx = c_dist(rng);
        int new_station = closest_stations[k][new_station_idx];

        if (new_station == current_station) {
            continue;
        }

        Solution next_sol = current_sol;
        next_sol.assignment[k] = new_station;
        next_sol.calculate_costs();

        long long diff = next_sol.total_cost - current_sol.total_cost;

        if (diff < 0 || (T > 0 && exp(-diff / T) > u_dist(rng))) {
            current_sol = next_sol;
            if (current_sol.total_cost < best_sol.total_cost) {
                best_sol = current_sol;
            }
        }
    }

    vector<int> b_out(M, 0);
    calculate_final_edges(best_sol.p, b_out);

    for (int i = 1; i <= N; ++i) {
        cout << best_sol.p[i] << (i == N ? "" : " ");
    }
    cout << endl;
    for (int i = 0; i < M; ++i) {
        cout << b_out[i] << (i == M - 1 ? "" : " ");
    }
    cout << endl;

    return 0;
}