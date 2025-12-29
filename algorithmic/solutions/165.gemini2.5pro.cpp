#include <iostream>
#include <vector>
#include <string>
#include <cmath>
#include <algorithm>
#include <chrono>
#include <random>
#include <numeric>

using namespace std;

const long long INF = 1e18;

int N, M;
int si, sj;
vector<string> A;
vector<string> t;

vector<vector<int>> overlap;
vector<pair<int, int>> char_pos[26];

mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

int calculate_overlap(const string& s1, const string& s2) {
    for (int k = 4; k >= 1; --k) {
        if (s1.substr(5 - k) == s2.substr(0, k)) {
            return k;
        }
    }
    return 0;
}

long long get_path_overlap(const vector<int>& path) {
    long long total_overlap = 0;
    for (size_t i = 0; i < path.size() - 1; ++i) {
        total_overlap += overlap[path[i]][path[i+1]];
    }
    return total_overlap;
}

long long get_ov(const vector<int>& path, int idx) {
    if (idx < 0 || idx >= (int)path.size() - 1) return 0;
    return overlap[path[idx]][path[idx+1]];
}

long long calculate_delta_ov_swap(const vector<int>& p, int i, int j) {
    if (i > j) swap(i, j);
    
    long long old_ov = get_ov(p, i-1) + get_ov(p, i) + get_ov(p, j-1) + get_ov(p, j);
    if (j == i + 1) old_ov -= get_ov(p, i);
    
    vector<int> p_new = p;
    swap(p_new[i], p_new[j]);

    long long new_ov = get_ov(p_new, i-1) + get_ov(p_new, i) + get_ov(p_new, j-1) + get_ov(p_new, j);
    if (j == i + 1) new_ov -= get_ov(p_new, i);

    return new_ov - old_ov;
}


int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    auto start_time = chrono::high_resolution_clock::now();

    cin >> N >> M;
    cin >> si >> sj;
    A.resize(N);
    for (int i = 0; i < N; ++i) {
        cin >> A[i];
        for (int j = 0; j < N; ++j) {
            char_pos[A[i][j] - 'A'].push_back({i, j});
        }
    }
    t.resize(M);
    for (int i = 0; i < M; ++i) {
        cin >> t[i];
    }

    overlap.assign(M, vector<int>(M, 0));
    for (int i = 0; i < M; ++i) {
        for (int j = 0; j < M; ++j) {
            if (i == j) continue;
            overlap[i][j] = calculate_overlap(t[i], t[j]);
        }
    }

    vector<vector<pair<int, int>>> adj(M);
    for(int i = 0; i < M; ++i) {
        for(int j = 0; j < M; ++j) {
            if(i == j) continue;
            adj[i].push_back({-overlap[i][j], j});
        }
        sort(adj[i].begin(), adj[i].end());
    }

    vector<int> best_path;
    long long max_ov = -1;

    for (int start_node = 0; start_node < M; ++start_node) {
        vector<int> path;
        path.push_back(start_node);
        vector<bool> visited(M, false);
        visited[start_node] = true;
        
        while ((int)path.size() < M) {
            int current_node = path.back();
            int best_next = -1;
            for(auto const& [ov_neg, next_node] : adj[current_node]) {
                if(!visited[next_node]) {
                    best_next = next_node;
                    break;
                }
            }
            if(best_next == -1) { 
                for(int i=0; i<M; ++i) if(!visited[i]) { best_next = i; break;}
            }
            path.push_back(best_next);
            visited[best_next] = true;
        }

        long long current_ov = get_path_overlap(path);
        if (max_ov == -1 || current_ov > max_ov) {
            max_ov = current_ov;
            best_path = path;
        }
    }

    vector<int> current_path = best_path;
    long long current_ov = max_ov;
    
    double start_temp = 5;
    double end_temp = 0.1;

    int iter_count = 0;
    while (true) {
        auto now = chrono::high_resolution_clock::now();
        double time_ratio = (double)chrono::duration_cast<chrono::milliseconds>(now - start_time).count() / 2800.0;
        if (time_ratio >= 1.0) break;
        
        iter_count++;

        int i = rng() % M;
        int j = rng() % M;
        if (i == j) continue;

        long long delta_ov = calculate_delta_ov_swap(current_path, i, j);
        
        double temp = start_temp * pow(end_temp / start_temp, time_ratio);
        if (delta_ov > 0 || (double)rng() / rng.max() < exp(delta_ov / temp)) {
            swap(current_path[i], current_path[j]);
            current_ov += delta_ov;
            if (current_ov > max_ov) {
                max_ov = current_ov;
                best_path = current_path;
            }
        }
    }

    string S = t[best_path[0]];
    for (size_t i = 1; i < best_path.size(); ++i) {
        int ov = overlap[best_path[i-1]][best_path[i]];
        S += t[best_path[i]].substr(ov);
    }

    int L = S.length();
    vector<vector<long long>> dp(N, vector<long long>(N, INF));
    vector<vector<vector<pair<int, int>>>> parents(L, vector<vector<pair<int, int>>>(N, vector<pair<int, int>>(N)));

    for (auto& p : char_pos[S[0] - 'A']) {
        dp[p.first][p.second] = abs(p.first - si) + abs(p.second - sj) + 1;
    }

    for (int k = 1; k < L; ++k) {
        vector<vector<long long>> g = dp;
        vector<vector<int>> g_parent_c(N, vector<int>(N));
        for(int r = 0; r < N; ++r) iota(g_parent_c[r].begin(), g_parent_c[r].end(), 0);

        for (int r = 0; r < N; ++r) {
            for (int c = 1; c < N; ++c) {
                if (g[r][c-1] + 1 < g[r][c]) {
                    g[r][c] = g[r][c-1] + 1;
                    g_parent_c[r][c] = g_parent_c[r][c-1];
                }
            }
            for (int c = N - 2; c >= 0; --c) {
                if (g[r][c+1] + 1 < g[r][c]) {
                    g[r][c] = g[r][c+1] + 1;
                    g_parent_c[r][c] = g_parent_c[r][c+1];
                }
            }
        }
        
        vector<vector<long long>> dist_grid = g;
        vector<vector<int>> dist_parent_r(N, vector<int>(N));
        for(int r = 0; r < N; ++r) dist_parent_r[r] = vector<int>(N, r);

        for (int c = 0; c < N; ++c) {
            for (int r = 1; r < N; ++r) {
                if (dist_grid[r-1][c] + 1 < dist_grid[r][c]) {
                    dist_grid[r][c] = dist_grid[r-1][c] + 1;
                    dist_parent_r[r][c] = dist_parent_r[r-1][c];
                }
            }
            for (int r = N - 2; r >= 0; --r) {
                 if (dist_grid[r+1][c] + 1 < dist_grid[r][c]) {
                    dist_grid[r][c] = dist_grid[r+1][c] + 1;
                    dist_parent_r[r][c] = dist_parent_r[r+1][c];
                }
            }
        }

        vector<vector<long long>> next_dp(N, vector<long long>(N, INF));
        for (auto& p : char_pos[S[k] - 'A']) {
            int r = p.first, c = p.second;
            if (dist_grid[r][c] < INF) {
                next_dp[r][c] = dist_grid[r][c] + 1;
                int pr = dist_parent_r[r][c];
                int pc = g_parent_c[pr][c];
                parents[k][r][c] = {pr, pc};
            }
        }
        dp = next_dp;
    }

    long long min_total_cost = INF;
    int last_r = -1, last_c = -1;
    for (int r = 0; r < N; ++r) {
        for (int c = 0; c < N; ++c) {
            if (dp[r][c] < min_total_cost) {
                min_total_cost = dp[r][c];
                last_r = r;
                last_c = c;
            }
        }
    }

    vector<pair<int, int>> result_path(L);
    result_path[L - 1] = {last_r, last_c};
    for (int k = L - 1; k >= 1; --k) {
        pair<int, int> p = parents[k][result_path[k].first][result_path[k].second];
        result_path[k - 1] = p;
    }

    for (const auto& p : result_path) {
        cout << p.first << " " << p.second << "\n";
    }

    return 0;
}