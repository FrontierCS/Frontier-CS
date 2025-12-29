#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <algorithm>
#include <map>
#include <chrono>
#include <random>
#include <cstring>

using namespace std;

const int N = 50;
int si, sj;
int t[N][N];
int p[N][N];

int max_tid = 0;
vector<vector<pair<int, int>>> tile_squares;
vector<long long> tile_scores;
vector<int> tile_size;

bool visited_squares[N][N];
vector<bool> visited_tiles;

const int dr[] = {-1, 1, 0, 0};
const int dc[] = {0, 0, -1, 1};

struct CandidateMove {
    double eval;
    string segment;
    int end_r, end_c;

    bool operator<(const CandidateMove& other) const {
        return eval > other.eval;
    }
};

void preprocess() {
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            max_tid = max(max_tid, t[i][j]);
        }
    }
    tile_squares.resize(max_tid + 1);
    tile_scores.resize(max_tid + 1, 0);
    tile_size.resize(max_tid + 1, 0);
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            int tid = t[i][j];
            tile_squares[tid].push_back({i, j});
            tile_scores[tid] += p[i][j];
        }
    }
    for (int i = 0; i <= max_tid; ++i) {
        tile_size[i] = tile_squares[i].size();
    }
}

string get_move_char(int r1, int c1, int r2, int c2) {
    if (r1 - 1 == r2 && c1 == c2) return "U";
    if (r1 + 1 == r2 && c1 == c2) return "D";
    if (r1 == r2 && c1 - 1 == c2) return "L";
    if (r1 == r2 && c1 + 1 == c2) return "R";
    return "";
}

string solve_single(double w, mt19937& rng) {
    int curr_r = si;
    int curr_c = sj;
    string path = "";

    memset(visited_squares, 0, sizeof(visited_squares));
    visited_tiles.assign(max_tid + 1, false);

    visited_squares[curr_r][curr_c] = true;
    visited_tiles[t[curr_r][curr_c]] = true;
    
    for (int step = 0; step < N * N * 2; ++step) {
        vector<CandidateMove> candidates;
        int current_tid = t[curr_r][curr_c];

        for (int d = 0; d < 4; ++d) {
            int nr = curr_r + dr[d];
            int nc = curr_c + dc[d];

            if (nr < 0 || nr >= N || nc < 0 || nc >= N) continue;
            if (visited_squares[nr][nc]) continue;

            int next_tid = t[nr][nc];
            
            if (next_tid == current_tid) {
                long long score_gain = p[nr][nc];
                int exit_r = nr, exit_c = nc;
                string segment = get_move_char(curr_r, curr_c, nr, nc);

                double future_score = 0;
                for (int d2 = 0; d2 < 4; ++d2) {
                    int nnr = exit_r + dr[d2];
                    int nnc = exit_c + dc[d2];
                    if (nnr < 0 || nnr >= N || nnc < 0 || nnc >= N) continue;
                    if (visited_squares[nnr][nnc]) continue;
                    int nnext_tid = t[nnr][nnc];
                    if (visited_tiles[nnext_tid]) continue;
                    future_score = max(future_score, (double)tile_scores[nnext_tid]);
                }
                
                double eval = score_gain + w * future_score;
                candidates.push_back({eval, segment, exit_r, exit_c});

            } else {
                if (visited_tiles[next_tid]) continue;
                
                long long score_gain = tile_scores[next_tid];
                int exit_r = nr, exit_c = nc;
                string segment = get_move_char(curr_r, curr_c, nr, nc);
                
                bool local_visited[N][N];
                memcpy(local_visited, visited_squares, sizeof(visited_squares));
                local_visited[nr][nc] = true;

                if (tile_size[next_tid] == 2) {
                    auto s1 = tile_squares[next_tid][0];
                    auto s2 = tile_squares[next_tid][1];
                    int other_r, other_c;
                    if (s1.first == nr && s1.second == nc) {
                        other_r = s2.first; other_c = s2.second;
                    } else {
                        other_r = s1.first; other_c = s1.second;
                    }
                    segment += get_move_char(nr, nc, other_r, other_c);
                    exit_r = other_r;
                    exit_c = other_c;
                    local_visited[exit_r][exit_c] = true;
                }

                double future_score = 0;
                for (int d2 = 0; d2 < 4; ++d2) {
                    int nnr = exit_r + dr[d2];
                    int nnc = exit_c + dc[d2];
                    if (nnr < 0 || nnr >= N || nnc < 0 || nnc >= N) continue;
                    if (local_visited[nnr][nnc]) continue;
                    int nnext_tid = t[nnr][nnc];
                    if (visited_tiles[nnext_tid] || nnext_tid == next_tid) continue;
                    future_score = max(future_score, (double)tile_scores[nnext_tid]);
                }
                
                double eval = score_gain + w * future_score;
                candidates.push_back({eval, segment, exit_r, exit_c});
            }
        }
        
        if (candidates.empty()) break;

        sort(candidates.begin(), candidates.end());
        
        int choice_idx = 0;
        if (!candidates.empty()) {
            int k = min((int)candidates.size(), 3);
            uniform_int_distribution<> dist(0, k - 1);
            choice_idx = dist(rng);
        }

        CandidateMove best_move = candidates[choice_idx];

        path += best_move.segment;
        int temp_r = curr_r, temp_c = curr_c;
        for (char move_char : best_move.segment) {
            if (move_char == 'U') temp_r--;
            else if (move_char == 'D') temp_r++;
            else if (move_char == 'L') temp_c--;
            else if (move_char == 'R') temp_c++;
            visited_squares[temp_r][temp_c] = true;
            visited_tiles[t[temp_r][temp_c]] = true;
        }
        curr_r = best_move.end_r;
        curr_c = best_move.end_c;
    }
    return path;
}


long long calculate_score(const string& path) {
    if (max_tid == 0 && !tile_squares.empty()) return 0;
    int r = si, c = sj;
    bool v_sq[N][N];
    memset(v_sq, 0, sizeof(v_sq));
    vector<bool> v_t(max_tid + 1, false);

    v_sq[r][c] = true;
    v_t[t[r][c]] = true;
    long long score = p[r][c];

    for (char move : path) {
        int pr = r, pc = c;
        if (move == 'U') r--;
        else if (move == 'D') r++;
        else if (move == 'L') c--;
        else if (move == 'R') c++;
        
        if (r < 0 || r >= N || c < 0 || c >= N) return -1;
        if (v_sq[r][c]) return -1;
        if (t[r][c] != t[pr][pc] && v_t[t[r][c]]) return -1;

        v_sq[r][c] = true;
        v_t[t[r][c]] = true;
        score += p[r][c];
    }
    return score;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    auto start_time = chrono::high_resolution_clock::now();

    cin >> si >> sj;
    for (int i = 0; i < N; ++i) for (int j = 0; j < N; ++j) cin >> t[i][j];
    for (int i = 0; i < N; ++i) for (int j = 0; j < N; ++j) cin >> p[i][j];

    preprocess();

    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());
    uniform_real_distribution<double> w_dist(0.1, 1.5);
    
    string best_path = "";
    long long best_score = -1;
    
    int time_limit = 1950;

    while(true) {
        auto current_time = chrono::high_resolution_clock::now();
        if (chrono::duration_cast<chrono::milliseconds>(current_time - start_time).count() > time_limit) {
            break;
        }

        double w = w_dist(rng);
        string current_path = solve_single(w, rng);
        long long current_score = calculate_score(current_path);

        if (current_score > best_score) {
            best_score = current_score;
            best_path = current_path;
        }
    }

    cout << best_path << endl;

    return 0;
}