#include <bits/stdc++.h>
using namespace std;

int di[4] = {0, -1, 0, 1};
int dj[4] = {-1, 0, 1, 0};
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

long long compute_score(int rot[30][30], int orig[30][30]) {
    int eff[30][30][4];
    for (int i = 0; i < 30; i++) {
        for (int j = 0; j < 30; j++) {
            int ori = orig[i][j];
            int rr = rot[i][j];
            for (int d = 0; d < 4; d++) {
                int drel = (d + rr) % 4;
                int outrel = base_to[ori][drel];
                if (outrel == -1) {
                    eff[i][j][d] = -1;
                } else {
                    eff[i][j][d] = (outrel - rr + 4) % 4;
                }
            }
        }
    }
    bool gvisited[30][30][4] = {false};
    vector<int> cycles;
    for (int si = 0; si < 30; si++) {
        for (int sj = 0; sj < 30; sj++) {
            for (int sd = 0; sd < 4; sd++) {
                if (eff[si][sj][sd] == -1 || gvisited[si][sj][sd]) continue;
                int local_id[30][30][4];
                memset(local_id, -1, sizeof(local_id));
                vector<tuple<int, int, int>> cpath;
                int ci = si, cj = sj, cd = sd;
                int step = 0;
                while (true) {
                    if (gvisited[ci][cj][cd]) {
                        break;
                    }
                    int lid = local_id[ci][cj][cd];
                    if (lid != -1) {
                        cycles.push_back(step - lid);
                        break;
                    }
                    local_id[ci][cj][cd] = step;
                    cpath.emplace_back(ci, cj, cd);
                    step++;
                    int d2 = eff[ci][cj][cd];
                    int ni = ci + di[d2];
                    int nj = cj + dj[d2];
                    if (ni < 0 || ni >= 30 || nj < 0 || nj >= 30) break;
                    int nd = (d2 + 2) % 4;
                    if (eff[ni][nj][nd] == -1) break;
                    ci = ni;
                    cj = nj;
                    cd = nd;
                }
                for (auto& p : cpath) {
                    int ii, jj, dd;
                    tie(ii, jj, dd) = p;
                    gvisited[ii][jj][dd] = true;
                }
            }
        }
    }
    if (cycles.empty()) return 0;
    sort(cycles.rbegin(), cycles.rend());
    if (cycles.size() < 2) return 0;
    return (long long)cycles[0] * cycles[1];
}

int main() {
    srand(time(NULL));
    vector<string> grid(30);
    for (auto& s : grid) cin >> s;
    int orig[30][30];
    for (int i = 0; i < 30; i++) {
        for (int j = 0; j < 30; j++) {
            orig[i][j] = grid[i][j] - '0';
        }
    }
    int best_rot[30][30];
    memset(best_rot, 0, sizeof(best_rot));
    long long best_score = compute_score(best_rot, orig);
    int current_rot[30][30];
    memcpy(current_rot, best_rot, sizeof(current_rot));
    long long current_score = best_score;
    double T = 10000.0;
    double cooling = 0.995;
    int max_moves = 50000;
    int moves = 0;
    while (T > 1.0 && moves < max_moves) {
        moves++;
        int i = rand() % 30;
        int j = rand() % 30;
        int old_r = current_rot[i][j];
        int new_r = rand() % 4;
        if (new_r == old_r) continue;
        current_rot[i][j] = new_r;
        long long new_score = compute_score(current_rot, orig);
        long long delta = new_score - current_score;
        double prob = (double)rand() / RAND_MAX;
        if (delta > 0 || prob < exp(delta / T)) {
            current_score = new_score;
            if (new_score > best_score) {
                best_score = new_score;
                memcpy(best_rot, current_rot, sizeof(current_rot));
            }
        } else {
            current_rot[i][j] = old_r;
        }
        T *= cooling;
    }
    string res = "";
    for (int i = 0; i < 30; i++) {
        for (int j = 0; j < 30; j++) {
            res += char('0' + best_rot[i][j]);
        }
    }
    cout << res << endl;
    return 0;
}