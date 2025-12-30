#include <iostream>
#include <vector>
#include <cmath>
#include <numeric>
#include <algorithm>
#include <chrono>
#include <random>
#include <tuple>
#include <queue>
#include <map>

using namespace std;

const long long INF = 4e18; 

struct Point {
    int x, y;
};

long long dist_sq(const Point& p1, const Point& p2) {
    long long dx = p1.x - p2.x;
    long long dy = p1.y - p2.y;
    return dx * dx + dy * dy;
}

int N, M, K;
vector<Point> stations;
vector<Point> residents;
vector<tuple<int, int, int>> edges;
vector<vector<pair<int, int>>> adj;
map<pair<int, int>, int> edge_to_idx;

vector<vector<long long>> sp_dist;
vector<vector<int>> sp_parent;

mt19937 rng(0);

auto start_time = chrono::steady_clock::now();
double time_limit = 2.95;

void dijkstra(int start_node) {
    sp_dist[start_node].assign(N + 1, INF);
    sp_parent[start_node].assign(N + 1, -1);
    sp_dist[start_node][start_node] = 0;
    priority_queue<pair<long long, int>, vector<pair<long long, int>>, greater<pair<long long, int>>> pq;
    pq.push({0, start_node});

    while (!pq.empty()) {
        auto [d, u] = pq.top();
        pq.pop();

        if (d > sp_dist[start_node][u]) {
            continue;
        }

        for (auto& edge : adj[u]) {
            int v = edge.first;
            int w = get<2>(edges[edge.second]);
            if (sp_dist[start_node][u] + w < sp_dist[start_node][v]) {
                sp_dist[start_node][v] = sp_dist[start_node][u] + w;
                sp_parent[start_node][v] = u;
                pq.push({sp_dist[start_node][v], v});
            }
        }
    }
}

long long calculate_cost(const vector<bool>& current_active, vector<int>& P, vector<int>& B) {
    vector<int> terminals;
    for (int i = 1; i <= N; ++i) {
        if (current_active[i]) {
            terminals.push_back(i);
        }
    }
    
    P.assign(N + 1, 0);
    long long power_cost = 0;
    vector<long long> station_max_dist_sq(N + 1, 0);
    for (int k = 0; k < K; ++k) {
        long long min_d_sq = -1;
        int best_station = -1;
        for (int i : terminals) {
             long long d_sq = dist_sq(stations[i], residents[k]);
             if (best_station == -1 || d_sq < min_d_sq) {
                 min_d_sq = d_sq;
                 best_station = i;
             }
        }
        if (best_station == -1 || round(sqrt(min_d_sq)) > 5000) {
            return INF;
        }
        station_max_dist_sq[best_station] = max(station_max_dist_sq[best_station], min_d_sq);
    }
    for (int i : terminals) {
        if (station_max_dist_sq[i] > 0) {
            int p = round(sqrt(station_max_dist_sq[i]));
            P[i] = p;
            power_cost += (long long)p * p;
        }
    }
    
    long long network_cost = 0;
    B.assign(M, 0);
    if (terminals.size() > 1) {
        vector<long long> min_cost_to_tree(N + 1, INF);
        vector<int> edge_to_tree(N + 1, -1);
        vector<bool> in_tree(N + 1, false);
        
        min_cost_to_tree[1] = 0;

        for (size_t i = 0; i < terminals.size(); ++i) {
            int u = -1;
            long long min_c = INF;
            for (int term : terminals) {
                if (!in_tree[term] && min_cost_to_tree[term] < min_c) {
                    min_c = min_cost_to_tree[term];
                    u = term;
                }
            }
            if (u == -1) break;

            in_tree[u] = true;
            if (u != 1) {
                network_cost += min_cost_to_tree[u];
            }
            for (int term : terminals) {
                if (!in_tree[term] && sp_dist[u][term] < min_cost_to_tree[term]) {
                    min_cost_to_tree[term] = sp_dist[u][term];
                    edge_to_tree[term] = u;
                }
            }
        }

        vector<bool> edge_on(M, false);
        for(int term : terminals) {
            if (edge_to_tree[term] != -1) {
                int u = edge_to_tree[term];
                int curr = term;
                while(curr != u) {
                    int p = sp_parent[u][curr];
                    int n1 = min(curr, p), n2 = max(curr, p);
                    edge_on[edge_to_idx.at({n1, n2})] = true;
                    curr = p;
                }
            }
        }
        for(int j=0; j<M; ++j) if(edge_on[j]) B[j] = 1;
    }
    
    return power_cost + network_cost;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    rng.seed(chrono::steady_clock::now().time_since_epoch().count());

    cin >> N >> M >> K;
    stations.resize(N + 1);
    residents.resize(K);
    adj.resize(N + 1);
    edges.resize(M);

    for (int i = 1; i <= N; ++i) cin >> stations[i].x >> stations[i].y;
    for (int i = 0; i < M; ++i) {
        int u, v, w;
        cin >> u >> v >> w;
        edges[i] = {u, v, w};
        adj[u].push_back({v, i});
        adj[v].push_back({u, i});
        if (u > v) swap(u,v);
        edge_to_idx[{u,v}] = i;
    }
    for (int i = 0; i < K; ++i) cin >> residents[i].x >> residents[i].y;

    sp_dist.resize(N + 1);
    sp_parent.resize(N + 1);
    for (int i = 1; i <= N; ++i) {
        dijkstra(i);
    }
    
    vector<bool> active_stations(N + 1, false);
    active_stations[1] = true;
    for (int k = 0; k < K; ++k) {
        long long min_d_sq = -1;
        int best_s = -1;
        for (int i = 1; i <= N; ++i) {
            long long d_sq = dist_sq(stations[i], residents[k]);
            if (best_s == -1 || d_sq < min_d_sq) {
                min_d_sq = d_sq;
                best_s = i;
            }
        }
        active_stations[best_s] = true;
    }

    while(true) {
        vector<int> current_terminals;
        for(int i=1; i<=N; ++i) if(active_stations[i]) current_terminals.push_back(i);
        
        int best_s_to_remove = -1;
        long long max_score_decrease = 0;
        
        vector<int> temp_P, temp_B;
        long long current_score = calculate_cost(active_stations, temp_P, temp_B);
        if (current_score >= INF) break;

        for(int s_to_remove : current_terminals) {
            if (s_to_remove == 1) continue;
            
            vector<bool> next_active = active_stations;
            next_active[s_to_remove] = false;
            
            long long next_score = calculate_cost(next_active, temp_P, temp_B);
            if (next_score < current_score) {
                if (current_score - next_score > max_score_decrease) {
                    max_score_decrease = current_score - next_score;
                    best_s_to_remove = s_to_remove;
                }
            }
        }
        if(best_s_to_remove != -1) {
            active_stations[best_s_to_remove] = false;
        } else {
            break;
        }
    }
    
    vector<int> best_P, best_B, current_P, current_B;
    long long current_score = calculate_cost(active_stations, current_P, current_B);
    long long best_score = current_score;
    best_P = current_P;
    best_B = current_B;
    
    double T_start = 1e8;
    double T_end = 1e2;
    
    while(true) {
        auto current_time = chrono::steady_clock::now();
        double elapsed_seconds = chrono::duration<double>(current_time - start_time).count();
        if (elapsed_seconds > time_limit) break;

        int station_to_change = (rng() % (N -1)) + 2;
        vector<bool> next_active = active_stations;
        next_active[station_to_change] = !next_active[station_to_change];

        vector<int> next_P, next_B;
        long long next_score = calculate_cost(next_active, next_P, next_B);

        if (next_score >= INF) continue;

        double temp = T_start + (T_end - T_start) * elapsed_seconds / time_limit;
        
        double acceptance_prob = exp((double)(current_score - next_score) / temp);

        if (acceptance_prob > (double)rng() / rng.max()) {
            active_stations = next_active;
            current_score = next_score;
            if (current_score < best_score) {
                best_score = current_score;
                best_P = next_P;
                best_B = next_B;
            }
        }
    }

    calculate_cost(active_stations, best_P, best_B);
     for (int i = 1; i <= N; ++i) {
        cout << best_P[i] << (i == N ? "" : " ");
    }
    cout << endl;
    for (int i = 0; i < M; ++i) {
        cout << best_B[i] << (i == M - 1 ? "" : " ");
    }
    cout << endl;

    return 0;
}