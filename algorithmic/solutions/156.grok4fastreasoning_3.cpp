#include <bits/stdc++.h>
using namespace std;

int base_to[8][4] = {
    {1, 0, -1, -1},
    {3, -1, -1, 0},
    {-1, -1, 3, 2},
    {-1, 2, 1, -1},
    {1, 0, 3, 2},
    {3, 2, 1, 0},
    {2, -1, 0, -1},
    {-1, 3, -1, 1}
};

int di[4] = {0, -1, 0, 1};
int dj[4] = {-1, 0, 1, 0};

vector<int> get_cycles(int eff[30][30][4]) {
    vector<int> cycles;
    bool global_vis[30][30][4];
    memset(global_vis, 0, sizeof(global_vis));
    for (int si = 0; si < 30; ++si) {
        for (int sj = 0; sj < 30; ++sj) {
            for (int sd = 0; sd < 4; ++sd) {
                if (eff[si][sj][sd] == -1 || global_vis[si][sj][sd]) continue;
                vector<tuple<int, int, int>> path;
                bool in_path[30][30][4];
                memset(in_path, 0, sizeof(in_path));
                int ci = si, cj = sj, cd = sd;
                while (true) {
                    if (global_vis[ci][cj][cd]) {
                        break;
                    }
                    global_vis[ci][cj][cd] = true;
                    in_path[ci][cj][cd] = true;
                    path.emplace_back(ci, cj, cd);
                    int d2 = eff[ci][cj][cd];
                    int ni = ci + di[d2];
                    int nj = cj + dj[d2];
                    if (ni < 0 || ni >= 30 || nj < 0 || nj >= 30) {
                        break;
                    }
                    int nd = (d2 + 2) % 4;
                    if (eff[ni][nj][nd] == -1) {
                        break;
                    }
                    ci = ni;
                    cj = nj;
                    cd = nd;
                    if (in_path[ci][cj][cd]) {
                        int cycle_start_idx = -1;
                        for (int k = 0; k < (int)path.size(); ++k) {
                            auto [pi, pj, pd] = path[k];
                            if (pi == ci && pj == cj && pd == cd) {
                                cycle_start_idx = k;
                                break;
                            }
                        }
                        if (cycle_start_idx != -1) {
                            int clen = path.size() - cycle_start_idx;
                            cycles.push_back(clen);
                        }
                        break;
                    }
                }
            }
        }
    }
    return cycles;
}

long long compute_score(int tile[30][30], int rot[30][30]) {
    int eff[30][30][4];
    for (int i = 0; i < 30; ++i) {
        for (int j = 0; j < 30; ++j) {
            int t = tile[i][j];
            int r = rot[i][j];
            for (int din = 0; din < 4; ++din) {
                int orig_din = (din + r) % 4;
                int orig_out = base_to[t][orig_din];
                if (orig_out == -1) {
                    eff[i][j][din] = -1;
                } else {
                    eff[i][j][din] = (orig_out - r + 4) % 4;
                }
            }
        }
    }
    vector<int> cls = get_cycles(eff);
    if (cls.size() < 2) return 0;
    sort(cls.rbegin(), cls.rend());
    return (long long)cls[0] * cls[1];
}

int main() {
    srand(time(0));
    int tile[30][30];
    for (int i = 0; i < 30; ++i) {
        string s;
        cin >> s;
        for (int j = 0; j < 30; ++j) {
            tile[i][j] = s[j] - '0';
        }
    }
    int best_rot[30][30];
    long long global_best = -1;
    int num_trials = 10;
    int steps_per_trial = 10000;
    // Trial 0: all zero
    {
        int current_rot[30][30] = {0};
        long long cur_score = compute_score(tile, current_rot);
        if (cur_score > global_best) {
            global_best = cur_score;
            memcpy(best_rot, current_rot, sizeof(current_rot));
        }
        for (int step = 0; step < steps_per_trial; ++step) {
            int ii = rand() % 30;
            int jj = rand() % 30;
            int old_r = current_rot[ii][jj];
            int nr = rand() % 4;
            if (nr == old_r) continue;
            current_rot[ii][jj] = nr;
            long long ns = compute_score(tile, current_rot);
            if (ns > cur_score) {
                cur_score = ns;
                if (cur_score > global_best) {
                    global_best = cur_score;
                    memcpy(best_rot, current_rot, sizeof(current_rot));
                }
            } else {
                current_rot[ii][jj] = old_r;
            }
        }
    }
    // Random trials
    for (int trial = 0; trial < num_trials; ++trial) {
        int current_rot[30][30];
        for (int i = 0; i < 30; ++i) {
            for (int j = 0; j < 30; ++j) {
                current_rot[i][j] = rand() % 4;
            }
        }
        long long cur_score = compute_score(tile, current_rot);
        if (cur_score > global_best) {
            global_best = cur_score;
            memcpy(best_rot, current_rot, sizeof(current_rot));
        }
        for (int step = 0; step < steps_per_trial; ++step) {
            int ii = rand() % 30;
            int jj = rand() % 30;
            int old_r = current_rot[ii][jj];
            int nr = rand() % 4;
            if (nr == old_r) continue;
            current_rot[ii][jj] = nr;
            long long ns = compute_score(tile, current_rot);
            if (ns > cur_score) {
                cur_score = ns;
                if (cur_score > global_best) {
                    global_best = cur_score;
                    memcpy(best_rot, current_rot, sizeof(current_rot));
                }
            } else {
                current_rot[ii][jj] = old_r;
            }
        }
    }
    string s(900, ' ');
    for (int i = 0; i < 30; ++i) {
        for (int j = 0; j < 30; ++j) {
            s[i * 30 + j] = '0' + best_rot[i][j];
        }
    }
    cout << s << endl;
    return 0;
}