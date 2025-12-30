#include <iostream>
#include <vector>
#include <string>
#include <cmath>
#include <algorithm>
#include <numeric>
#include <chrono>
#include <random>
#include <deque>

using namespace std;

const long long INF = 1e18;

int N, M;
int si, sj;
vector<string> A;
vector<string> t;
vector<vector<pair<int, int>>> pos;
vector<vector<int>> overlap_matrix;

int calculate_overlap(const string& s1, const string& s2) {
    for (int k = 4; k > 0; --k) {
        if (s1.substr(5 - k) == s2.substr(0, k)) {
            return k;
        }
    }
    return 0;
}

void precompute_overlaps() {
    overlap_matrix.assign(M, vector<int>(M, 0));
    for (int i = 0; i < M; ++i) {
        for (int j = 0; j < M; ++j) {
            if (i == j) continue;
            overlap_matrix[i][j] = calculate_overlap(t[i], t[j]);
        }
    }
}

vector<int> nn_tsp(int start_node) {
    vector<int> path;
    path.push_back(start_node);
    vector<bool> visited(M, false);
    visited[start_node] = true;
    int current_node = start_node;

    for (int i = 0; i < M - 1; ++i) {
        int best_next = -1;
        int max_ov = -1;
        for (int next_node = 0; next_node < M; ++next_node) {
            if (!visited[next_node]) {
                if (overlap_matrix[current_node][next_node] > max_ov) {
                    max_ov = overlap_matrix[current_node][next_node];
                    best_next = next_node;
                }
            }
        }
        if (best_next == -1) {
            for(int next_node = 0; next_node < M; ++next_node) {
                if(!visited[next_node]) {
                    best_next = next_node;
                    break;
                }
            }
        }
        path.push_back(best_next);
        visited[best_next] = true;
        current_node = best_next;
    }
    return path;
}

vector<int> double_ended_nn_tsp() {
    if (M <= 1) {
        if (M == 1) return {0};
        return {};
    }
    
    int best_u = -1, best_v = -1, max_ov = -1;
    for (int i = 0; i < M; ++i) {
        for (int j = 0; j < M; ++j) {
            if (i == j) continue;
            if (overlap_matrix[i][j] > max_ov) {
                max_ov = overlap_matrix[i][j];
                best_u = i;
                best_v = j;
            }
        }
    }

    deque<int> path;
    path.push_back(best_u);
    path.push_back(best_v);
    vector<bool> visited(M, false);
    visited[best_u] = true;
    visited[best_v] = true;

    for (int i = 0; i < M - 2; ++i) {
        int path_start = path.front();
        int path_end = path.back();
        
        int best_prev = -1, max_ov_prev = -1;
        for (int prev_node = 0; prev_node < M; ++prev_node) {
            if (!visited[prev_node]) {
                if (overlap_matrix[prev_node][path_start] > max_ov_prev) {
                    max_ov_prev = overlap_matrix[prev_node][path_start];
                    best_prev = prev_node;
                }
            }
        }

        int best_next = -1, max_ov_next = -1;
        for (int next_node = 0; next_node < M; ++next_node) {
            if (!visited[next_node]) {
                if (overlap_matrix[path_end][next_node] > max_ov_next) {
                    max_ov_next = overlap_matrix[path_end][next_node];
                    best_next = next_node;
                }
            }
        }

        if (max_ov_prev > max_ov_next) {
            path.push_front(best_prev);
            visited[best_prev] = true;
        } else if (best_next != -1) {
            path.push_back(best_next);
            visited[best_next] = true;
        } else if (best_prev != -1) {
            path.push_front(best_prev);
            visited[best_prev] = true;
        } else {
            for(int node=0; node<M; ++node) {
                if(!visited[node]) {
                    path.push_back(node);
                    visited[node] = true;
                    break;
                }
            }
        }
    }
    return vector<int>(path.begin(), path.end());
}


pair<long long, vector<pair<int, int>>> solve_typing(const string& S) {
    int len = S.length();
    if (len == 0) return {0, {}};
    if (len > 5000) return {INF, {}};

    vector<vector<long long>> dp1(N, vector<long long>(N, INF));
    vector<vector<long long>> dp2(N, vector<long long>(N, INF));
    vector<vector<vector<pair<int, int>>>> parent(len, vector<vector<pair<int, int>>>(N, vector<pair<int, int>>(N, {-1, -1})));
    
    auto *dp_prev = &dp1;
    auto *dp_curr = &dp2;
    (*dp_prev)[si][sj] = 0;

    for (int k = 0; k < len; ++k) {
        vector<vector<long long>> dist_dp = *dp_prev;
        vector<vector<pair<int, int>>> source(N, vector<pair<int, int>>(N));
        for(int i=0; i<N; ++i) for(int j=0; j<N; ++j) if(dist_dp[i][j] != INF) source[i][j] = {i,j}; else source[i][j] = {-1,-1};

        for (int i = 0; i < N; ++i) {
            for (int j = 1; j < N; ++j) {
                if (dist_dp[i][j-1] != INF && dist_dp[i][j-1] + 1 < dist_dp[i][j]) {
                    dist_dp[i][j] = dist_dp[i][j-1] + 1;
                    source[i][j] = source[i][j-1];
                }
            }
            for (int j = N - 2; j >= 0; --j) {
                if (dist_dp[i][j+1] != INF && dist_dp[i][j+1] + 1 < dist_dp[i][j]) {
                    dist_dp[i][j] = dist_dp[i][j+1] + 1;
                    source[i][j] = source[i][j+1];
                }
            }
        }
        for (int j = 0; j < N; ++j) {
            for (int i = 1; i < N; ++i) {
                if (dist_dp[i-1][j] != INF && dist_dp[i-1][j] + 1 < dist_dp[i][j]) {
                    dist_dp[i][j] = dist_dp[i-1][j] + 1;
                    source[i][j] = source[i-1][j];
                }
            }
            for (int i = N - 2; i >= 0; --i) {
                if (dist_dp[i+1][j] != INF && dist_dp[i+1][j] + 1 < dist_dp[i][j]) {
                    dist_dp[i][j] = dist_dp[i+1][j] + 1;
                    source[i][j] = source[i+1][j];
                }
            }
        }

        fill(dp_curr->begin(), dp_curr->end(), vector<long long>(N, INF));
        char target_char = S[k];
        for (const auto& p : pos[target_char - 'A']) {
            int r = p.first;
            int c = p.second;
            if (dist_dp[r][c] != INF) {
                (*dp_curr)[r][c] = dist_dp[r][c] + 1;
                parent[k][r][c] = source[r][c];
            }
        }
        swap(dp_prev, dp_curr);
    }

    long long min_cost = INF;
    pair<int, int> final_pos = {-1, -1};
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            if ((*dp_prev)[i][j] < min_cost) {
                min_cost = (*dp_prev)[i][j];
                final_pos = {i, j};
            }
        }
    }
    
    if (min_cost == INF) return {INF, {}};

    vector<pair<int, int>> path(len);
    pair<int, int> curr_pos = final_pos;
    for (int k = len - 1; k >= 0; --k) {
        path[k] = curr_pos;
        curr_pos = parent[k][curr_pos.first][curr_pos.second];
    }
    
    return {min_cost, path};
}


int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> N >> M;
    cin >> si >> sj;
    A.resize(N);
    pos.resize(26);
    for (int i = 0; i < N; ++i) {
        cin >> A[i];
        for (int j = 0; j < N; ++j) {
            pos[A[i][j] - 'A'].push_back({i, j});
        }
    }
    t.resize(M);
    for (int i = 0; i < M; ++i) {
        cin >> t[i];
    }

    precompute_overlaps();

    vector<vector<int>> tsp_paths;
    if (M > 0) {
        tsp_paths.push_back(double_ended_nn_tsp());
    
        mt19937 rng(0);
        vector<int> p(M);
        iota(p.begin(), p.end(), 0);
        
        int num_starts = min(M, 49);
        shuffle(p.begin(), p.end(), rng);

        for(int i = 0; i < num_starts; ++i) {
            tsp_paths.push_back(nn_tsp(p[i]));
        }
    }

    long long best_cost = INF;
    vector<pair<int, int>> best_path;

    for (const auto& path_indices : tsp_paths) {
        if (path_indices.empty()) continue;
        string S = t[path_indices[0]];
        for (size_t i = 0; i < path_indices.size() - 1; ++i) {
            int u = path_indices[i];
            int v = path_indices[i+1];
            int ov = overlap_matrix[u][v];
            S += t[v].substr(ov);
        }

        auto result = solve_typing(S);
        if (result.first < best_cost) {
            best_cost = result.first;
            best_path = result.second;
        }
    }
    
    if (M > 0) {
        for (const auto& p : best_path) {
            cout << p.first << " " << p.second << "\n";
        }
    }

    return 0;
}