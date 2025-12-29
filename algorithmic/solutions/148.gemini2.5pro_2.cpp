#include <iostream>
#include <vector>
#include <string>
#include <chrono>
#include <random>
#include <algorithm>
#include <tuple>

using namespace std;

const int N = 50;
int si, sj;
int t[N][N];
int p[N][N];

int max_tid = 0;
vector<vector<pair<int, int>>> tile_squares;
vector<long long> tile_score;

int dr[] = {-1, 1, 0, 0};
int dc[] = {0, 0, -1, 1};
char move_char[] = {'U', 'D', 'L', 'R'};

struct Path {
    string moves;
    long long score;
};

double evaluate_move(int next_tid, const vector<bool>& visited_tiles, double lookahead_factor) {
    double score1 = tile_score[next_tid];
    double max_score2 = 0;
    
    for (auto const& sq : tile_squares[next_tid]) {
        int r = sq.first;
        int c = sq.second;
        for (int i = 0; i < 4; ++i) {
            int nr = r + dr[i];
            int nc = c + dc[i];
            if (nr >= 0 && nr < N && nc >= 0 && nc < N) {
                int future_tid = t[nr][nc];
                if (!visited_tiles[future_tid] && future_tid != next_tid) {
                    max_score2 = max(max_score2, (double)tile_score[future_tid]);
                }
            }
        }
    }
    return score1 + lookahead_factor * max_score2;
}


Path generate_path(mt19937& rng, double lookahead_factor) {
    int cr = si, cc = sj;
    string path_str = "";
    vector<bool> visited_tiles(max_tid + 1, false);
    vector<vector<bool>> visited_sq(N, vector<bool>(N, false));

    long long current_score = p[si][sj];
    visited_sq[si][sj] = true;
    
    int start_tid = t[cr][cc];
    visited_tiles[start_tid] = true;
    
    while (true) {
        int curr_tid = t[cr][cc];
        
        vector<tuple<double, pair<int, int>, pair<int, int>>> candidates;

        for (auto const& exit_sq : tile_squares[curr_tid]) {
            int r = exit_sq.first;
            int c = exit_sq.second;
            for (int i = 0; i < 4; ++i) {
                int nr = r + dr[i];
                int nc = c + dc[i];
                if (nr >= 0 && nr < N && nc >= 0 && nc < N) {
                    int next_tid = t[nr][nc];
                    if (!visited_tiles[next_tid]) {
                        double val = evaluate_move(next_tid, visited_tiles, lookahead_factor);
                        candidates.emplace_back(val, exit_sq, make_pair(nr, nc));
                    }
                }
            }
        }

        if (candidates.empty()) {
            break;
        }

        sort(candidates.rbegin(), candidates.rend());
        
        vector<tuple<double, pair<int, int>, pair<int, int>>> unique_candidates;
        vector<bool> seen_tids(max_tid+1, false);
        for(const auto& cand : candidates) {
            int next_tid = t[get<2>(cand).first][get<2>(cand).second];
            if (!seen_tids[next_tid]) {
                unique_candidates.push_back(cand);
                seen_tids[next_tid] = true;
            }
        }
        
        int k = min((int)unique_candidates.size(), 3);
        if (k == 0) break;
        int choice_idx = uniform_int_distribution<int>(0, k-1)(rng);
        
        auto [val, best_exit_sq, best_next_sq] = unique_candidates[choice_idx];

        if (cr != best_exit_sq.first || cc != best_exit_sq.second) {
            if (best_exit_sq.first == cr + 1) path_str += 'D';
            else if (best_exit_sq.first == cr - 1) path_str += 'U';
            else if (best_exit_sq.second == cc + 1) path_str += 'R';
            else path_str += 'L';
            cr = best_exit_sq.first;
            cc = best_exit_sq.second;
            if (!visited_sq[cr][cc]) {
                current_score += p[cr][cc];
                visited_sq[cr][cc] = true;
            }
        }

        if (best_next_sq.first == cr + 1) path_str += 'D';
        else if (best_next_sq.first == cr - 1) path_str += 'U';
        else if (best_next_sq.second == cc + 1) path_str += 'R';
        else path_str += 'L';
        cr = best_next_sq.first;
        cc = best_next_sq.second;
        if (!visited_sq[cr][cc]) {
            current_score += p[cr][cc];
            visited_sq[cr][cc] = true;
        }
        
        int next_tid = t[cr][cc];
        visited_tiles[next_tid] = true;
    }
    
    return {path_str, current_score};
}

void precompute() {
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            max_tid = max(max_tid, t[i][j]);
        }
    }
    tile_squares.resize(max_tid + 1);
    tile_score.resize(max_tid + 1, 0);
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            tile_squares[t[i][j]].push_back({i, j});
            tile_score[t[i][j]] += p[i][j];
        }
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    auto start_time = chrono::high_resolution_clock::now();

    cin >> si >> sj;
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            cin >> t[i][j];
        }
    }
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            cin >> p[i][j];
        }
    }

    precompute();

    Path best_path = {"", -1};
    
    random_device rd;
    mt19937 rng(rd());

    while (true) {
        auto current_time = chrono::high_resolution_clock::now();
        auto elapsed = chrono::duration_cast<chrono::milliseconds>(current_time - start_time).count();
        if (elapsed > 2950) {
            break;
        }
        
        double lookahead_factor = uniform_real_distribution<double>(0.2, 0.8)(rng);
        Path current_path = generate_path(rng, lookahead_factor);
        if (current_path.score > best_path.score) {
            best_path = current_path;
        }
    }

    cout << best_path.moves << endl;

    return 0;
}