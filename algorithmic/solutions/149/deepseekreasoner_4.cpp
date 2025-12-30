#include <iostream>
#include <vector>
#include <queue>
#include <cmath>
#include <algorithm>
#include <string>
#include <limits>

using namespace std;

const int N = 30;
const double INF = 1e18;
const double INIT_WEIGHT = 5000.0;
const double MIN_WEIGHT = 100.0;
const double MAX_WEIGHT = 10000.0;
const double BASE_LR = 0.5;

double h[N][N-1];      // horizontal edges: h[i][j] between (i,j) and (i,j+1)
double v[N-1][N];      // vertical edges: v[i][j] between (i,j) and (i+1,j)
int h_count[N][N-1] = {0};
int v_count[N-1][N] = {0};

// Directions: U, D, L, R
const int dx[4] = {-1, 1, 0, 0};
const int dy[4] = {0, 0, -1, 1};
const char dir_char[4] = {'U', 'D', 'L', 'R'};

// Node id: i*N + j

double dijkstra(int si, int sj, int ti, int tj, vector<char>& path, vector<pair<char, pair<int,int>>>& edges) {
    int src = si * N + sj;
    int tar = ti * N + tj;
    vector<double> dist(N*N, INF);
    vector<int> prev(N*N, -1);
    vector<char> prev_dir(N*N, ' ');
    dist[src] = 0.0;
    using pdi = pair<double, int>;
    priority_queue<pdi, vector<pdi>, greater<pdi>> pq;
    pq.push({0.0, src});
    
    while (!pq.empty()) {
        auto [d, u] = pq.top(); pq.pop();
        if (d > dist[u]) continue;
        if (u == tar) break;
        int i = u / N;
        int j = u % N;
        // Explore four neighbors
        for (int k = 0; k < 4; ++k) {
            int ni = i + dx[k];
            int nj = j + dy[k];
            if (ni < 0 || ni >= N || nj < 0 || nj >= N) continue;
            int v = ni * N + nj;
            double w = 0.0;
            // Determine edge weight
            if (k == 0) { // U: (i,j) -> (i-1,j) uses vertical edge at (i-1,j)
                if (i > 0) w = v[i-1][j];
                else continue;
            } else if (k == 1) { // D: (i,j) -> (i+1,j) uses vertical edge at (i,j)
                if (i < N-1) w = v[i][j];
                else continue;
            } else if (k == 2) { // L: (i,j) -> (i,j-1) uses horizontal edge at (i,j-1)
                if (j > 0) w = h[i][j-1];
                else continue;
            } else { // k == 3, R: (i,j) -> (i,j+1) uses horizontal edge at (i,j)
                if (j < N-1) w = h[i][j];
                else continue;
            }
            if (dist[u] + w < dist[v]) {
                dist[v] = dist[u] + w;
                prev[v] = u;
                prev_dir[v] = dir_char[k];
                pq.push({dist[v], v});
            }
        }
    }
    
    // Reconstruct path from target to source
    path.clear();
    edges.clear();
    double total_pred = 0.0;
    int cur = tar;
    while (cur != src) {
        int pre = prev[cur];
        char d = prev_dir[cur];
        path.push_back(d);
        // Determine edge used
        int pi = pre / N, pj = pre % N;
        int ci = cur / N, cj = cur % N;
        if (d == 'R') {
            edges.push_back({'H', {pi, pj}});
            total_pred += h[pi][pj];
        } else if (d == 'L') {
            edges.push_back({'H', {pi, pj-1}});
            total_pred += h[pi][pj-1];
        } else if (d == 'D') {
            edges.push_back({'V', {pi, pj}});
            total_pred += v[pi][pj];
        } else { // 'U'
            edges.push_back({'V', {pi-1, pj}});
            total_pred += v[pi-1][pj];
        }
        cur = pre;
    }
    reverse(path.begin(), path.end());
    // edges are in reverse order, but order doesn't matter for update
    return total_pred;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    // Initialize edge weights
    for (int i = 0; i < N; ++i)
        for (int j = 0; j < N-1; ++j)
            h[i][j] = INIT_WEIGHT;
    for (int i = 0; i < N-1; ++i)
        for (int j = 0; j < N; ++j)
            v[i][j] = INIT_WEIGHT;
    
    for (int k = 0; k < 1000; ++k) {
        int si, sj, ti, tj;
        cin >> si >> sj >> ti >> tj;
        
        vector<char> path;
        vector<pair<char, pair<int,int>>> edges;
        double pred_len = dijkstra(si, sj, ti, tj, path, edges);
        
        // Output path
        for (char c : path) cout << c;
        cout << endl;
        
        int observed;
        cin >> observed;
        
        // Update edge weights along the path
        double ratio = (double)observed / pred_len;
        for (auto& e : edges) {
            char type = e.first;
            int i = e.second.first;
            int j = e.second.second;
            if (type == 'H') {
                h_count[i][j]++;
                double lr = BASE_LR / sqrt(h_count[i][j]);
                double new_val = h[i][j] * (1.0 + lr * (ratio - 1.0));
                if (new_val < MIN_WEIGHT) new_val = MIN_WEIGHT;
                if (new_val > MAX_WEIGHT) new_val = MAX_WEIGHT;
                h[i][j] = new_val;
            } else { // 'V'
                v_count[i][j]++;
                double lr = BASE_LR / sqrt(v_count[i][j]);
                double new_val = v[i][j] * (1.0 + lr * (ratio - 1.0));
                if (new_val < MIN_WEIGHT) new_val = MIN_WEIGHT;
                if (new_val > MAX_WEIGHT) new_val = MAX_WEIGHT;
                v[i][j] = new_val;
            }
        }
    }
    
    return 0;
}