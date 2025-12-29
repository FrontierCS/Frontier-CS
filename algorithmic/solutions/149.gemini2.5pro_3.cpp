#include <iostream>
#include <vector>
#include <string>
#include <queue>
#include <cmath>
#include <numeric>
#include <algorithm>

using namespace std;

const int GRID_SIZE = 30;

// Phase 1 estimates
double h_est[GRID_SIZE][GRID_SIZE - 1];
double v_est[GRID_SIZE - 1][GRID_SIZE];
double h_cnt[GRID_SIZE][GRID_SIZE - 1];
double v_cnt[GRID_SIZE - 1][GRID_SIZE];

// Phase 2 model
bool is_h_split[GRID_SIZE];
int h_split_pos[GRID_SIZE];
double h_seg_est[GRID_SIZE][2];
double h_seg_cnt[GRID_SIZE][2];

bool is_v_split[GRID_SIZE];
int v_split_pos[GRID_SIZE];
double v_seg_est[GRID_SIZE][2];
double v_seg_cnt[GRID_SIZE][2];

// Dijkstra variables
double dist[GRID_SIZE][GRID_SIZE];
pair<int, int> parent[GRID_SIZE][GRID_SIZE];
char move_char[GRID_SIZE][GRID_SIZE];

const int dr[] = {-1, 1, 0, 0};
const int dc[] = {0, 0, -1, 1};
const char moves[] = {'U', 'D', 'L', 'R'};

string find_path(int si, int sj, int ti, int tj, int k) {
    for (int i = 0; i < GRID_SIZE; ++i) {
        for (int j = 0; j < GRID_SIZE; ++j) {
            dist[i][j] = 1e18;
        }
    }

    dist[si][sj] = 0;
    priority_queue<pair<double, pair<int, int>>, vector<pair<double, pair<int, int>>>, greater<pair<double, pair<int, int>>>> pq;
    pq.push({0, {si, sj}});

    bool phase2 = k >= 400;

    while (!pq.empty()) {
        auto [d, curr] = pq.top();
        pq.pop();
        int r = curr.first;
        int c = curr.second;

        if (d > dist[r][c]) {
            continue;
        }
        if (r == ti && c == tj) {
            break;
        }
        
        for (int i = 0; i < 4; ++i) {
            int nr = r + dr[i];
            int nc = c + dc[i];

            if (nr < 0 || nr >= GRID_SIZE || nc < 0 || nc >= GRID_SIZE) {
                continue;
            }

            double edge_cost;
            if (moves[i] == 'U') {
                if (phase2) {
                    edge_cost = is_v_split[c] && r - 1 >= v_split_pos[c] ? v_seg_est[c][1] : v_seg_est[c][0];
                } else {
                    edge_cost = v_est[r-1][c];
                }
            } else if (moves[i] == 'D') {
                if (phase2) {
                    edge_cost = is_v_split[c] && r >= v_split_pos[c] ? v_seg_est[c][1] : v_seg_est[c][0];
                } else {
                    edge_cost = v_est[r][c];
                }
            } else if (moves[i] == 'L') {
                if (phase2) {
                    edge_cost = is_h_split[r] && c - 1 >= h_split_pos[r] ? h_seg_est[r][1] : h_seg_est[r][0];
                } else {
                    edge_cost = h_est[r][c-1];
                }
            } else { // 'R'
                if (phase2) {
                    edge_cost = is_h_split[r] && c >= h_split_pos[r] ? h_seg_est[r][1] : h_seg_est[r][0];
                } else {
                    edge_cost = h_est[r][c];
                }
            }

            if (dist[r][c] + edge_cost < dist[nr][nc]) {
                dist[nr][nc] = dist[r][c] + edge_cost;
                parent[nr][nc] = {r, c};
                move_char[nr][nc] = moves[i];
                pq.push({dist[nr][nc], {nr, nc}});
            }
        }
    }

    string path = "";
    int cur_r = ti, cur_c = tj;
    while (cur_r != si || cur_c != sj) {
        path += move_char[cur_r][cur_c];
        auto p = parent[cur_r][cur_c];
        cur_r = p.first;
        cur_c = p.second;
    }
    reverse(path.begin(), path.end());
    return path;
}


int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    for (int i = 0; i < GRID_SIZE; ++i) {
        for (int j = 0; j < GRID_SIZE - 1; ++j) {
            h_est[i][j] = 5000;
            h_cnt[i][j] = 0;
        }
    }
    for (int i = 0; i < GRID_SIZE - 1; ++i) {
        for (int j = 0; j < GRID_SIZE; ++j) {
            v_est[i][j] = 5000;
            v_cnt[i][j] = 0;
        }
    }

    const int K_switch = 400;
    const double C_alpha = 5.0;
    const double beta = 0.3;
    const double SPLIT_THRESHOLD = 0.75;
    
    for (int k = 0; k < 1000; ++k) {
        int si, sj, ti, tj;
        cin >> si >> sj >> ti >> tj;
        
        if (k == K_switch) {
            // Horizontal edges
            for (int i = 0; i < GRID_SIZE; ++i) {
                double total_h_cnt = 0;
                double w_mean_h = 0;
                for (int j = 0; j < GRID_SIZE - 1; ++j) {
                    total_h_cnt += h_cnt[i][j];
                    w_mean_h += h_est[i][j] * h_cnt[i][j];
                }
                if (total_h_cnt > 0) w_mean_h /= total_h_cnt; else w_mean_h = 5000;

                double sse1 = 0;
                for (int j = 0; j < GRID_SIZE - 1; ++j) {
                    sse1 += h_cnt[i][j] * pow(h_est[i][j] - w_mean_h, 2);
                }

                double min_sse2 = 1e18;
                int best_x = -1;
                for (int x = 1; x < GRID_SIZE - 1; ++x) {
                    double p1_cnt = 0, p1_mean = 0;
                    for (int j = 0; j < x; ++j) { p1_cnt += h_cnt[i][j]; p1_mean += h_est[i][j] * h_cnt[i][j]; }
                    if (p1_cnt > 0) p1_mean /= p1_cnt; else continue;

                    double p2_cnt = 0, p2_mean = 0;
                    for (int j = x; j < GRID_SIZE - 1; ++j) { p2_cnt += h_cnt[i][j]; p2_mean += h_est[i][j] * h_cnt[i][j]; }
                    if (p2_cnt > 0) p2_mean /= p2_cnt; else continue;

                    double sse2 = 0;
                    for (int j = 0; j < x; ++j) sse2 += h_cnt[i][j] * pow(h_est[i][j] - p1_mean, 2);
                    for (int j = x; j < GRID_SIZE - 1; ++j) sse2 += h_cnt[i][j] * pow(h_est[i][j] - p2_mean, 2);
                    
                    if (sse2 < min_sse2) {
                        min_sse2 = sse2;
                        best_x = x;
                    }
                }

                if (best_x != -1 && min_sse2 < SPLIT_THRESHOLD * sse1) {
                    is_h_split[i] = true;
                    h_split_pos[i] = best_x;
                    double p1_cnt = 0, p1_mean = 0, p2_cnt = 0, p2_mean = 0;
                    for(int j=0; j<best_x; ++j) { p1_cnt += h_cnt[i][j]; p1_mean += h_est[i][j]*h_cnt[i][j]; }
                    for(int j=best_x; j<GRID_SIZE-1; ++j) { p2_cnt += h_cnt[i][j]; p2_mean += h_est[i][j]*h_cnt[i][j]; }
                    h_seg_est[i][0] = (p1_cnt > 0) ? p1_mean / p1_cnt : 5000;
                    h_seg_est[i][1] = (p2_cnt > 0) ? p2_mean / p2_cnt : 5000;
                    h_seg_cnt[i][0] = p1_cnt;
                    h_seg_cnt[i][1] = p2_cnt;
                } else {
                    is_h_split[i] = false;
                    h_seg_est[i][0] = w_mean_h;
                    h_seg_cnt[i][0] = total_h_cnt;
                }
            }
            // Vertical edges
            for (int j = 0; j < GRID_SIZE; ++j) {
                double total_v_cnt = 0;
                double w_mean_v = 0;
                for (int i = 0; i < GRID_SIZE - 1; ++i) {
                    total_v_cnt += v_cnt[i][j];
                    w_mean_v += v_est[i][j] * v_cnt[i][j];
                }
                if (total_v_cnt > 0) w_mean_v /= total_v_cnt; else w_mean_v = 5000;

                double sse1 = 0;
                for (int i = 0; i < GRID_SIZE - 1; ++i) {
                    sse1 += v_cnt[i][j] * pow(v_est[i][j] - w_mean_v, 2);
                }

                double min_sse2 = 1e18;
                int best_y = -1;
                for (int y = 1; y < GRID_SIZE - 1; ++y) {
                    double p1_cnt = 0, p1_mean = 0;
                    for (int i = 0; i < y; ++i) { p1_cnt += v_cnt[i][j]; p1_mean += v_est[i][j] * v_cnt[i][j]; }
                    if(p1_cnt > 0) p1_mean /= p1_cnt; else continue;

                    double p2_cnt = 0, p2_mean = 0;
                    for (int i = y; i < GRID_SIZE-1; ++i) { p2_cnt += v_cnt[i][j]; p2_mean += v_est[i][j] * v_cnt[i][j]; }
                    if(p2_cnt > 0) p2_mean /= p2_cnt; else continue;

                    double sse2 = 0;
                    for (int i = 0; i < y; ++i) sse2 += v_cnt[i][j] * pow(v_est[i][j] - p1_mean, 2);
                    for (int i = y; i < GRID_SIZE-1; ++i) sse2 += v_cnt[i][j] * pow(v_est[i][j] - p2_mean, 2);
                    
                    if (sse2 < min_sse2) {
                        min_sse2 = sse2;
                        best_y = y;
                    }
                }

                if (best_y != -1 && min_sse2 < SPLIT_THRESHOLD * sse1) {
                    is_v_split[j] = true;
                    v_split_pos[j] = best_y;
                    double p1_cnt = 0, p1_mean = 0, p2_cnt = 0, p2_mean = 0;
                    for(int i=0; i<best_y; ++i) { p1_cnt += v_cnt[i][j]; p1_mean += v_est[i][j]*v_cnt[i][j]; }
                    for(int i=best_y; i<GRID_SIZE-1; ++i) { p2_cnt += v_cnt[i][j]; p2_mean += v_est[i][j]*v_cnt[i][j]; }
                    v_seg_est[j][0] = (p1_cnt > 0) ? p1_mean / p1_cnt : 5000;
                    v_seg_est[j][1] = (p2_cnt > 0) ? p2_mean / p2_cnt : 5000;
                    v_seg_cnt[j][0] = p1_cnt;
                    v_seg_cnt[j][1] = p2_cnt;
                } else {
                    is_v_split[j] = false;
                    v_seg_est[j][0] = w_mean_v;
                    v_seg_cnt[j][0] = total_v_cnt;
                }
            }
        }
        
        string path = find_path(si, sj, ti, tj, k);
        cout << path << endl;

        long long b_noisy;
        cin >> b_noisy;

        double b_est = 0;
        int cur_r = si, cur_c = sj;
        for (char move : path) {
            if (move == 'U') {
                if (k < K_switch) b_est += v_est[cur_r - 1][cur_c]; else b_est += is_v_split[cur_c] && cur_r - 1 >= v_split_pos[cur_c] ? v_seg_est[cur_c][1] : v_seg_est[cur_c][0];
                cur_r--;
            } else if (move == 'D') {
                if (k < K_switch) b_est += v_est[cur_r][cur_c]; else b_est += is_v_split[cur_c] && cur_r >= v_split_pos[cur_c] ? v_seg_est[cur_c][1] : v_seg_est[cur_c][0];
                cur_r++;
            } else if (move == 'L') {
                if (k < K_switch) b_est += h_est[cur_r][cur_c - 1]; else b_est += is_h_split[cur_r] && cur_c - 1 >= h_split_pos[cur_r] ? h_seg_est[cur_r][1] : h_seg_est[cur_r][0];
                cur_c--;
            } else { // 'R'
                if (k < K_switch) b_est += h_est[cur_r][cur_c]; else b_est += is_h_split[cur_r] && cur_c >= h_split_pos[cur_r] ? h_seg_est[cur_r][1] : h_seg_est[cur_r][0];
                cur_c++;
            }
        }

        double ratio = b_noisy / b_est;
        cur_r = si; cur_c = sj;
        for (char move : path) {
            if (k < K_switch) {
                if (move == 'U') {
                    double alpha = 1.0 / (v_cnt[cur_r-1][cur_c] + C_alpha);
                    v_est[cur_r-1][cur_c] = v_est[cur_r-1][cur_c] * (1-alpha) + v_est[cur_r-1][cur_c] * ratio * alpha;
                    v_cnt[cur_r-1][cur_c]++;
                    cur_r--;
                } else if (move == 'D') {
                    double alpha = 1.0 / (v_cnt[cur_r][cur_c] + C_alpha);
                    v_est[cur_r][cur_c] = v_est[cur_r][cur_c] * (1-alpha) + v_est[cur_r][cur_c] * ratio * alpha;
                    v_cnt[cur_r][cur_c]++;
                    cur_r++;
                } else if (move == 'L') {
                    double alpha = 1.0 / (h_cnt[cur_r][cur_c-1] + C_alpha);
                    h_est[cur_r][cur_c-1] = h_est[cur_r][cur_c-1] * (1-alpha) + h_est[cur_r][cur_c-1] * ratio * alpha;
                    h_cnt[cur_r][cur_c-1]++;
                    cur_c--;
                } else { // 'R'
                    double alpha = 1.0 / (h_cnt[cur_r][cur_c] + C_alpha);
                    h_est[cur_r][cur_c] = h_est[cur_r][cur_c] * (1-alpha) + h_est[cur_r][cur_c] * ratio * alpha;
                    h_cnt[cur_r][cur_c]++;
                    cur_c++;
                }
            } else {
                 if (move == 'U') {
                    int seg = is_v_split[cur_c] && cur_r - 1 >= v_split_pos[cur_c] ? 1 : 0;
                    double alpha = 1.0 / (v_seg_cnt[cur_c][seg] + C_alpha);
                    v_seg_est[cur_c][seg] = v_seg_est[cur_c][seg] * (1-alpha) + v_seg_est[cur_c][seg] * ratio * alpha;
                    v_seg_cnt[cur_c][seg]++;
                    cur_r--;
                } else if (move == 'D') {
                    int seg = is_v_split[cur_c] && cur_r >= v_split_pos[cur_c] ? 1 : 0;
                    double alpha = 1.0 / (v_seg_cnt[cur_c][seg] + C_alpha);
                    v_seg_est[cur_c][seg] = v_seg_est[cur_c][seg] * (1-alpha) + v_seg_est[cur_c][seg] * ratio * alpha;
                    v_seg_cnt[cur_c][seg]++;
                    cur_r++;
                } else if (move == 'L') {
                    int seg = is_h_split[cur_r] && cur_c - 1 >= h_split_pos[cur_r] ? 1 : 0;
                    double alpha = 1.0 / (h_seg_cnt[cur_r][seg] + C_alpha);
                    h_seg_est[cur_r][seg] = h_seg_est[cur_r][seg] * (1-alpha) + h_seg_est[cur_r][seg] * ratio * alpha;
                    h_seg_cnt[cur_r][seg]++;
                    cur_c--;
                } else { // 'R'
                    int seg = is_h_split[cur_r] && cur_c >= h_split_pos[cur_r] ? 1 : 0;
                    double alpha = 1.0 / (h_seg_cnt[cur_r][seg] + C_alpha);
                    h_seg_est[cur_r][seg] = h_seg_est[cur_r][seg] * (1-alpha) + h_seg_est[cur_r][seg] * ratio * alpha;
                    h_seg_cnt[cur_r][seg]++;
                    cur_c++;
                }
            }
        }
        
        if (k < K_switch) {
            double h_est_tmp[GRID_SIZE][GRID_SIZE-1];
            double v_est_tmp[GRID_SIZE-1][GRID_SIZE];
            for(int i=0; i<GRID_SIZE; ++i) for(int j=0; j<GRID_SIZE-1; ++j) h_est_tmp[i][j] = h_est[i][j];
            for(int i=0; i<GRID_SIZE-1; ++i) for(int j=0; j<GRID_SIZE; ++j) v_est_tmp[i][j] = v_est[i][j];

            for(int i=0; i<GRID_SIZE; ++i) {
                h_est[i][0] = h_est_tmp[i][0]*(1-beta/2) + h_est_tmp[i][1]*beta/2;
                for(int j=1; j<GRID_SIZE-2; ++j) {
                    h_est[i][j] = h_est_tmp[i][j]*(1-beta) + (h_est_tmp[i][j-1]+h_est_tmp[i][j+1])*beta/2;
                }
                h_est[i][GRID_SIZE-2] = h_est_tmp[i][GRID_SIZE-2]*(1-beta/2) + h_est_tmp[i][GRID_SIZE-3]*beta/2;
            }

            for(int j=0; j<GRID_SIZE; ++j) {
                v_est[0][j] = v_est_tmp[0][j]*(1-beta/2) + v_est_tmp[1][j]*beta/2;
                for(int i=1; i<GRID_SIZE-2; ++i) {
                    v_est[i][j] = v_est_tmp[i][j]*(1-beta) + (v_est_tmp[i-1][j]+v_est_tmp[i+1][j])*beta/2;
                }
                v_est[GRID_SIZE-2][j] = v_est_tmp[GRID_SIZE-2][j]*(1-beta/2) + v_est_tmp[GRID_SIZE-3][j]*beta/2;
            }
        }
    }

    return 0;
}