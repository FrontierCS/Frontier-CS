#include <iostream>
#include <vector>
#include <string>
#include <chrono>
#include <random>
#include <numeric>
#include <algorithm>
#include <set>
#include <cmath>

using namespace std;

// --- Timer to respect the time limit ---
using namespace std::chrono;
auto start_time = high_resolution_clock::now();
bool time_limit_exceeded() {
    auto current_time = high_resolution_clock::now();
    auto duration = duration_cast<milliseconds>(current_time - start_time);
    return duration.count() > 1950;
}

// --- Random number generator ---
mt19937 rng(0); 

// --- Constants & Global Variables ---
const int N = 50;
int si, sj;
int t[N][N];
int p[N][N];

int M = 0; // Number of unique tiles
vector<pair<int, int>> tile_squares[N * N];
long long tile_score[N * N];
pair<int, int> partner[N][N];
vector<int> adj_tiles[N * N];
bool tile_visited[N * N];

int dr[] = {-1, 1, 0, 0};
int dc[] = {0, 0, -1, 1};
char moves[] = "UDLR";

// Hyperparameters for the greedy evaluation and randomization
double ALPHA = 0.2;
double BETA = 2.0;

// --- Preprocessing ---
void preprocess() {
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            M = max(M, t[i][j] + 1);
        }
    }
    for (int i = 0; i < M; ++i) {
        tile_score[i] = 0;
    }
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            tile_squares[t[i][j]].push_back({i, j});
            tile_score[t[i][j]] += p[i][j];
        }
    }
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            partner[i][j] = {-1, -1};
        }
    }
    for (int i = 0; i < M; ++i) {
        if (tile_squares[i].size() == 2) {
            auto sq1 = tile_squares[i][0];
            auto sq2 = tile_squares[i][1];
            partner[sq1.first][sq1.second] = sq2;
            partner[sq2.first][sq2.second] = sq1;
        }
    }

    vector<set<int>> adj_sets(M);
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            for (int k = 0; k < 4; ++k) {
                int ni = i + dr[k];
                int nj = j + dc[k];
                if (ni >= 0 && ni < N && nj >= 0 && nj < N && t[i][j] != t[ni][nj]) {
                    adj_sets[t[i][j]].insert(t[ni][nj]);
                    adj_sets[t[ni][nj]].insert(t[i][j]);
                }
            }
        }
    }
    for (int i = 0; i < M; ++i) {
        for (int neighbor_tile : adj_sets[i]) {
            adj_tiles[i].push_back(neighbor_tile);
        }
    }
}

string get_move(pair<int, int> from, pair<int, int> to) {
    if (to.first == from.first - 1) return "U";
    if (to.first == from.first + 1) return "D";
    if (to.second == from.second - 1) return "L";
    if (to.second == from.second + 1) return "R";
    return "";
}

// --- Core Greedy Pathfinding Logic ---
pair<string, long long> solve_greedy(int start_r, int start_c, bool is_random) {
    string path = "";
    long long score = 0;
    int cur_r = start_r;
    int cur_c = start_c;

    while (true) {
        vector<pair<int, int>> candidates;
        vector<double> evals;

        for (int k = 0; k < 4; ++k) {
            int ni = cur_r + dr[k];
            int nj = cur_c + dc[k];

            if (ni >= 0 && ni < N && nj >= 0 && nj < N && !tile_visited[t[ni][nj]]) {
                candidates.push_back({ni, nj});
                double future_score = 0;
                for (int adj : adj_tiles[t[ni][nj]]) {
                    if (!tile_visited[adj]) {
                        future_score += tile_score[adj];
                    }
                }
                double current_eval = tile_score[t[ni][nj]] + ALPHA * future_score;
                evals.push_back(current_eval);
            }
        }

        if (candidates.empty()) break;

        int best_idx = -1;
        if (!is_random) {
            double max_eval = -1.0;
            for (size_t i = 0; i < candidates.size(); ++i) {
                if (evals[i] > max_eval) {
                    max_eval = evals[i];
                    best_idx = i;
                }
            }
        } else {
            vector<double> weights;
            double sum_weights = 0;
            for(double e : evals) {
                double w = pow(max(1.0, e), BETA);
                weights.push_back(w);
                sum_weights += w;
            }
            if (sum_weights < 1e-9) {
                 best_idx = uniform_int_distribution<int>(0, candidates.size() - 1)(rng);
            } else {
                uniform_real_distribution<double> dist(0, sum_weights);
                double r = dist(rng);
                double current_sum = 0;
                for (size_t i = 0; i < candidates.size(); ++i) {
                    current_sum += weights[i];
                    if (r <= current_sum) {
                        best_idx = i;
                        break;
                    }
                }
                if (best_idx == -1) best_idx = candidates.size() - 1;
            }
        }
        
        pair<int, int> next_pos = candidates[best_idx];
        path += get_move({cur_r, cur_c}, next_pos);
        cur_r = next_pos.first;
        cur_c = next_pos.second;
        
        int new_tile_id = t[cur_r][cur_c];
        tile_visited[new_tile_id] = true;
        score += tile_score[new_tile_id];

        if (partner[cur_r][cur_c].first != -1) {
            pair<int, int> p_pos = partner[cur_r][cur_c];
            path += get_move({cur_r, cur_c}, p_pos);
            cur_r = p_pos.first;
            cur_c = p_pos.second;
        }
    }
    return {path, score};
}

// --- Helper for Iterative Improvement ---
void trace_path(const string& path, int len, int& out_r, int& out_c, long long& out_score) {
    fill(tile_visited, tile_visited + M, false);
    
    int start_tile_id = t[si][sj];
    tile_visited[start_tile_id] = true;
    out_score = tile_score[start_tile_id];
    
    int cur_r = si, cur_c = sj;

    for (int i = 0; i < len; ++i) {
        char move = path[i];
        int k;
        for(k=0; k<4; ++k) if(moves[k] == move) break;
        int next_r = cur_r + dr[k];
        int next_c = cur_c + dc[k];
        
        int next_tile_id = t[next_r][next_c];
        if (!tile_visited[next_tile_id]) {
            tile_visited[next_tile_id] = true;
            out_score += tile_score[next_tile_id];
        }
        cur_r = next_r;
        cur_c = next_c;
    }
    out_r = cur_r;
    out_c = cur_c;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    cin >> si >> sj;
    for (int i = 0; i < N; ++i) for (int j = 0; j < N; ++j) cin >> t[i][j];
    for (int i = 0; i < N; ++i) for (int j = 0; j < N; ++j) cin >> p[i][j];

    preprocess();

    string best_path;
    long long best_score = -1;

    // --- Initial solution with deterministic greedy ---
    // Option 1: Start exploring from (si, sj)
    fill(tile_visited, tile_visited + M, false);
    tile_visited[t[si][sj]] = true;
    auto res1 = solve_greedy(si, sj, false);
    long long score1 = tile_score[t[si][sj]] + res1.second;
    if (score1 > best_score) {
        best_score = score1;
        best_path = res1.first;
    }

    // Option 2: If start tile is 2-square, move to partner first
    if (partner[si][sj].first != -1) {
        fill(tile_visited, tile_visited + M, false);
        tile_visited[t[si][sj]] = true;
        pair<int, int> p_pos = partner[si][sj];
        string initial_move = get_move({si, sj}, p_pos);
        auto res2 = solve_greedy(p_pos.first, p_pos.second, false);
        long long score2 = tile_score[t[si][sj]] + res2.second;
        if (score2 > best_score) {
            best_score = score2;
            best_path = initial_move + res2.first;
        }
    }

    // --- Iterative Improvement with Randomized Hill Climbing ---
    while (!time_limit_exceeded()) {
        int k = 0;
        if (!best_path.empty()) {
            k = uniform_int_distribution<int>(0, best_path.length())(rng);
        }

        int prefix_r, prefix_c;
        long long prefix_score;
        trace_path(best_path, k, prefix_r, prefix_c, prefix_score);
        
        auto suffix_res = solve_greedy(prefix_r, prefix_c, true);

        long long new_score = prefix_score + suffix_res.second;
        if (new_score > best_score) {
            best_score = new_score;
            best_path = best_path.substr(0, k) + suffix_res.first;
        }
    }

    cout << best_path << endl;

    return 0;
}