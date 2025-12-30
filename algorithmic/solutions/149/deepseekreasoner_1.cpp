#include <iostream>
#include <vector>
#include <queue>
#include <algorithm>
#include <cmath>
#include <random>
#include <cstring>

using namespace std;

const int N = 30;
const double INF = 1e18;
const double INIT_MEAN = 5000.0;
const double INIT_STD = 2000.0;
const double MIN_VAR = 100.0;
const double NOISE_REL = 0.05;

double h_mean[N][N-1];
double h_var[N][N-1];
double v_mean[N-1][N];
double v_var[N-1][N];

// random number generator
mt19937 rng(12345);

int main() {
    // initialize
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N-1; ++j) {
            h_mean[i][j] = INIT_MEAN;
            h_var[i][j] = INIT_STD * INIT_STD;
        }
    }
    for (int i = 0; i < N-1; ++i) {
        for (int j = 0; j < N; ++j) {
            v_mean[i][j] = INIT_MEAN;
            v_var[i][j] = INIT_STD * INIT_STD;
        }
    }

    for (int q = 0; q < 1000; ++q) {
        int si, sj, ti, tj;
        cin >> si >> sj >> ti >> tj;

        // sample edge weights
        double h_sampled[N][N-1];
        double v_sampled[N-1][N];
        normal_distribution<double> dist_normal;
        for (int i = 0; i < N; ++i) {
            for (int j = 0; j < N-1; ++j) {
                double mean = h_mean[i][j];
                double std = sqrt(h_var[i][j]);
                double w = mean + dist_normal(rng) * std;
                if (w < 1.0) w = 1.0;
                h_sampled[i][j] = w;
            }
        }
        for (int i = 0; i < N-1; ++i) {
            for (int j = 0; j < N; ++j) {
                double mean = v_mean[i][j];
                double std = sqrt(v_var[i][j]);
                double w = mean + dist_normal(rng) * std;
                if (w < 1.0) w = 1.0;
                v_sampled[i][j] = w;
            }
        }

        // Dijkstra
        int start = si * N + sj;
        int target = ti * N + tj;
        vector<double> dist(N*N, INF);
        vector<int> prev_vertex(N*N, -1);
        vector<char> prev_move(N*N, ' ');
        dist[start] = 0.0;
        priority_queue<pair<double, int>, vector<pair<double, int>>, greater<pair<double, int>>> pq;
        pq.push({0.0, start});

        while (!pq.empty()) {
            auto [d, u] = pq.top(); pq.pop();
            if (d > dist[u]) continue;
            if (u == target) break;
            int i = u / N;
            int j = u % N;

            // left
            if (j > 0) {
                int v = i * N + (j - 1);
                double w = h_sampled[i][j-1];
                if (dist[u] + w < dist[v]) {
                    dist[v] = dist[u] + w;
                    prev_vertex[v] = u;
                    prev_move[v] = 'L';
                    pq.push({dist[v], v});
                }
            }
            // right
            if (j < N-1) {
                int v = i * N + (j + 1);
                double w = h_sampled[i][j];
                if (dist[u] + w < dist[v]) {
                    dist[v] = dist[u] + w;
                    prev_vertex[v] = u;
                    prev_move[v] = 'R';
                    pq.push({dist[v], v});
                }
            }
            // up
            if (i > 0) {
                int v = (i-1) * N + j;
                double w = v_sampled[i-1][j];
                if (dist[u] + w < dist[v]) {
                    dist[v] = dist[u] + w;
                    prev_vertex[v] = u;
                    prev_move[v] = 'U';
                    pq.push({dist[v], v});
                }
            }
            // down
            if (i < N-1) {
                int v = (i+1) * N + j;
                double w = v_sampled[i][j];
                if (dist[u] + w < dist[v]) {
                    dist[v] = dist[u] + w;
                    prev_vertex[v] = u;
                    prev_move[v] = 'D';
                    pq.push({dist[v], v});
                }
            }
        }

        // reconstruct path
        vector<char> moves;
        int cur = target;
        while (cur != start) {
            moves.push_back(prev_move[cur]);
            cur = prev_vertex[cur];
        }
        reverse(moves.begin(), moves.end());
        string path(moves.begin(), moves.end());
        cout << path << endl;
        cout.flush();

        // read observed length
        int y;
        cin >> y;

        // collect edges along the path
        vector<pair<int, pair<int, int>>> edges; // 0 for horizontal, 1 for vertical; (i,j)
        int ci = si, cj = sj;
        for (char move : moves) {
            if (move == 'L') {
                edges.push_back({0, {ci, cj-1}}); // h[ci][cj-1]
                cj--;
            } else if (move == 'R') {
                edges.push_back({0, {ci, cj}}); // h[ci][cj]
                cj++;
            } else if (move == 'U') {
                edges.push_back({1, {ci-1, cj}}); // v[ci-1][cj]
                ci--;
            } else if (move == 'D') {
                edges.push_back({1, {ci, cj}}); // v[ci][cj]
                ci++;
            }
        }

        // compute prior sum and variance
        double M = 0.0;
        double V = 0.0;
        for (auto& edge : edges) {
            int type = edge.first;
            int i = edge.second.first;
            int j = edge.second.second;
            if (type == 0) {
                M += h_mean[i][j];
                V += h_var[i][j];
            } else {
                M += v_mean[i][j];
                V += v_var[i][j];
            }
        }

        double noise_std = NOISE_REL * max(M, 1000.0);
        double noise_var = noise_std * noise_std;
        double total_var = V + noise_var;
        double error = y - M;

        // update each edge
        for (auto& edge : edges) {
            int type = edge.first;
            int i = edge.second.first;
            int j = edge.second.second;
            if (type == 0) {
                double var_e = h_var[i][j];
                double delta = (var_e / total_var) * error;
                h_mean[i][j] += delta;
                h_var[i][j] = var_e - (var_e * var_e) / total_var;
                if (h_var[i][j] < MIN_VAR) h_var[i][j] = MIN_VAR;
            } else {
                double var_e = v_var[i][j];
                double delta = (var_e / total_var) * error;
                v_mean[i][j] += delta;
                v_var[i][j] = var_e - (var_e * var_e) / total_var;
                if (v_var[i][j] < MIN_VAR) v_var[i][j] = MIN_VAR;
            }
        }
    }

    return 0;
}