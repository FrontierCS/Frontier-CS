#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <random>
#include <tuple>
#include <cstring>

using namespace std;

const int N = 50;
const int N_ITER = 200;
const double EPSILON = 0.1;
const double W_FREE = 50.0;
const double W_SECOND = 0.5;

int di[4] = {-1, 1, 0, 0};
int dj[4] = {0, 0, -1, 1};
char dir_c[4] = {'U', 'D', 'L', 'R'};

int p[N][N];
int t[N][N];
int partner_i[N][N];
int partner_j[N][N];
int M;

void compute_partners() {
    for (int i = 0; i < N; ++i)
        for (int j = 0; j < N; ++j)
            partner_i[i][j] = partner_j[i][j] = -1;
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            if (partner_i[i][j] != -1) continue;
            for (int d = 0; d < 4; ++d) {
                int ni = i + di[d], nj = j + dj[d];
                if (ni >= 0 && ni < N && nj >= 0 && nj < N && t[ni][nj] == t[i][j]) {
                    partner_i[i][j] = ni;
                    partner_j[i][j] = nj;
                    partner_i[ni][nj] = i;
                    partner_j[ni][nj] = j;
                    break;
                }
            }
        }
    }
}

pair<string, int> greedy_run(int si, int sj, mt19937& rng) {
    bool visited_tile[M];
    memset(visited_tile, 0, sizeof(visited_tile));
    bool visited_cell[N][N] = {false};
    int ci = si, cj = sj;
    visited_tile[t[ci][cj]] = true;
    visited_cell[ci][cj] = true;
    int score = p[ci][cj];
    string path = "";
    uniform_real_distribution<double> dist(0.0, 1.0);
    while (true) {
        vector<tuple<int, int, char>> cands;
        for (int d = 0; d < 4; ++d) {
            int ni = ci + di[d], nj = cj + dj[d];
            if (ni >= 0 && ni < N && nj >= 0 && nj < N && !visited_cell[ni][nj] && !visited_tile[t[ni][nj]]) {
                cands.emplace_back(ni, nj, dir_c[d]);
            }
        }
        if (cands.empty()) break;
        vector<double> values(cands.size());
        for (size_t idx = 0; idx < cands.size(); ++idx) {
            int ni = get<0>(cands[idx]), nj = get<1>(cands[idx]);
            double val = p[ni][nj];
            // Count free neighbors after moving to (ni,nj)
            int free_cnt = 0;
            for (int dd = 0; dd < 4; ++dd) {
                int nni = ni + di[dd], nnj = nj + dj[dd];
                if (nni >= 0 && nni < N && nnj >= 0 && nnj < N && !visited_cell[nni][nnj] && !visited_tile[t[nni][nnj]]) {
                    // Exclude the partner cell of (ni,nj)
                    if (partner_i[ni][nj] != -1 && nni == partner_i[ni][nj] && nnj == partner_j[ni][nj])
                        continue;
                    free_cnt++;
                }
            }
            val += W_FREE * free_cnt;
            // Look ahead one more step
            double best_second = 0.0;
            for (int dd = 0; dd < 4; ++dd) {
                int nni = ni + di[dd], nnj = nj + dj[dd];
                if (nni >= 0 && nni < N && nnj >= 0 && nnj < N && !visited_cell[nni][nnj] && !visited_tile[t[nni][nnj]]) {
                    if (partner_i[ni][nj] != -1 && nni == partner_i[ni][nj] && nnj == partner_j[ni][nj])
                        continue;
                    int free_cnt2 = 0;
                    for (int ddd = 0; ddd < 4; ++ddd) {
                        int nnni = nni + di[ddd], nnnj = nnj + dj[ddd];
                        if (nnni >= 0 && nnni < N && nnnj >= 0 && nnnj < N &&
                            !visited_cell[nnni][nnnj] && !visited_tile[t[nnni][nnnj]]) {
                            if (partner_i[nni][nnj] != -1 && nnni == partner_i[nni][nnj] && nnnj == partner_j[nni][nnj])
                                continue;
                            free_cnt2++;
                        }
                    }
                    double val2 = p[nni][nnj] + W_FREE * free_cnt2;
                    if (val2 > best_second) best_second = val2;
                }
            }
            val += W_SECOND * best_second;
            values[idx] = val;
        }
        int chosen_idx;
        if (dist(rng) < EPSILON) {
            uniform_int_distribution<int> int_dist(0, cands.size() - 1);
            chosen_idx = int_dist(rng);
        } else {
            double best_val = -1e18;
            vector<int> best_ids;
            for (size_t i = 0; i < cands.size(); ++i) {
                if (values[i] > best_val) {
                    best_val = values[i];
                    best_ids.clear();
                    best_ids.push_back(i);
                } else if (values[i] == best_val) {
                    best_ids.push_back(i);
                }
            }
            uniform_int_distribution<int> int_dist(0, best_ids.size() - 1);
            chosen_idx = best_ids[int_dist(rng)];
        }
        // Perform move
        auto [ni, nj, ch] = cands[chosen_idx];
        ci = ni;
        cj = nj;
        visited_tile[t[ci][cj]] = true;
        visited_cell[ci][cj] = true;
        score += p[ci][cj];
        path += ch;
    }
    return {path, score};
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int si, sj;
    cin >> si >> sj;
    M = 0;
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            cin >> t[i][j];
            if (t[i][j] > M) M = t[i][j];
        }
    }
    M++; // number of tiles
    for (int i = 0; i < N; ++i)
        for (int j = 0; j < N; ++j)
            cin >> p[i][j];
    compute_partners();
    mt19937 rng(12345); // fixed seed for reproducibility
    string best_path = "";
    int best_score = -1;
    for (int iter = 0; iter < N_ITER; ++iter) {
        auto [path, score] = greedy_run(si, sj, rng);
        if (score > best_score) {
            best_score = score;
            best_path = path;
        }
        // shuffle the rng for next iteration
        rng.seed(rng() + 123);
    }
    cout << best_path << endl;
    return 0;
}