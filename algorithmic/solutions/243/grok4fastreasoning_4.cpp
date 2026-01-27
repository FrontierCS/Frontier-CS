#include <bits/stdc++.h>
using namespace std;

int main() {
    int R, C;
    cin >> R >> C;
    vector<string> mp(R);
    for (int i = 0; i < R; i++) cin >> mp[i];
    int DX[4] = {-1, 0, 1, 0};
    int DY[4] = {0, 1, 0, -1};
    int dists[101][101][4];
    memset(dists, 0, sizeof(dists));
    for (int i = 0; i < R; i++) {
        for (int j = 0; j < C; j++) {
            if (mp[i][j] != '.') continue;
            for (int dd = 0; dd < 4; dd++) {
                int di = DX[dd], dj = DY[dd];
                int ni = i + di, nj = j + dj;
                int cnt = 0;
                while (ni >= 0 && ni < R && nj >= 0 && nj < C && mp[ni][nj] == '.') {
                    cnt++;
                    ni += di;
                    nj += dj;
                }
                dists[i][j][dd] = cnt;
            }
        }
    }
    bool poss[101][101][4];
    memset(poss, 0, sizeof(poss));
    for (int i = 0; i < R; i++) {
        for (int j = 0; j < C; j++) {
            if (mp[i][j] == '.') {
                for (int d = 0; d < 4; d++) poss[i][j][d] = true;
            }
        }
    }
    int round_cnt = 0;
    while (true) {
        int current_d;
        cin >> current_d;
        if (current_d == -1) return 0;
        round_cnt++;
        if (round_cnt > 10000) {
            cout << "no" << endl;
            return 0;
        }
        bool newp[101][101][4] = {0};
        for (int i = 0; i < R; i++) {
            for (int j = 0; j < C; j++) {
                if (mp[i][j] == '.') {
                    for (int dd = 0; dd < 4; dd++) {
                        if (poss[i][j][dd] && dists[i][j][dd] == current_d) {
                            newp[i][j][dd] = true;
                        }
                    }
                }
            }
        }
        memcpy(poss, newp, sizeof(poss));
        set<pair<int, int>> act;
        int tot_st = 0;
        for (int i = 0; i < R; i++) {
            for (int j = 0; j < C; j++) {
                for (int dd = 0; dd < 4; dd++) {
                    if (poss[i][j][dd]) {
                        act.insert({i, j});
                        tot_st++;
                    }
                }
            }
        }
        if (act.size() == 1) {
            pair<int, int> p = *act.begin();
            cout << "yes " << p.first + 1 << " " << p.second + 1 << endl;
            return 0;
        }
        if (tot_st == 0) {
            cout << "no" << endl;
            return 0;
        }
        bool can_step = (current_d >= 1);
        int best_maxg = tot_st + 1;
        string best_a = "";
        if (can_step) {
            bool tmp[101][101][4] = {0};
            for (int i = 0; i < R; i++) {
                for (int j = 0; j < C; j++) {
                    for (int dd = 0; dd < 4; dd++) {
                        if (poss[i][j][dd]) {
                            int ni = i + DX[dd];
                            int nj = j + DY[dd];
                            if (ni >= 0 && ni < R && nj >= 0 && nj < C && mp[ni][nj] == '.') {
                                tmp[ni][nj][dd] = true;
                            }
                        }
                    }
                }
            }
            int cntt[100] = {0};
            for (int i = 0; i < R; i++) {
                for (int j = 0; j < C; j++) {
                    for (int dd = 0; dd < 4; dd++) {
                        if (tmp[i][j][dd]) {
                            int exd = dists[i][j][dd];
                            if (exd < 100) cntt[exd]++;
                        }
                    }
                }
            }
            int mg = 0;
            for (int k = 0; k < 100; k++) mg = max(mg, cntt[k]);
            if (mg < best_maxg) {
                best_maxg = mg;
                best_a = "step";
            }
        }
        {
            bool tmp[101][101][4] = {0};
            for (int i = 0; i < R; i++) {
                for (int j = 0; j < C; j++) {
                    for (int dd = 0; dd < 4; dd++) {
                        if (poss[i][j][dd]) {
                            int ndd = (dd + 1) % 4;
                            tmp[i][j][ndd] = true;
                        }
                    }
                }
            }
            int cntt[100] = {0};
            for (int i = 0; i < R; i++) {
                for (int j = 0; j < C; j++) {
                    for (int dd = 0; dd < 4; dd++) {
                        if (tmp[i][j][dd]) {
                            int exd = dists[i][j][dd];
                            if (exd < 100) cntt[exd]++;
                        }
                    }
                }
            }
            int mg = 0;
            for (int k = 0; k < 100; k++) mg = max(mg, cntt[k]);
            if (mg < best_maxg) {
                best_maxg = mg;
                best_a = "right";
            }
        }
        {
            bool tmp[101][101][4] = {0};
            for (int i = 0; i < R; i++) {
                for (int j = 0; j < C; j++) {
                    for (int dd = 0; dd < 4; dd++) {
                        if (poss[i][j][dd]) {
                            int ndd = (dd + 3) % 4;
                            tmp[i][j][ndd] = true;
                        }
                    }
                }
            }
            int cntt[100] = {0};
            for (int i = 0; i < R; i++) {
                for (int j = 0; j < C; j++) {
                    for (int dd = 0; dd < 4; dd++) {
                        if (tmp[i][j][dd]) {
                            int exd = dists[i][j][dd];
                            if (exd < 100) cntt[exd]++;
                        }
                    }
                }
            }
            int mg = 0;
            for (int k = 0; k < 100; k++) mg = max(mg, cntt[k]);
            if (mg < best_maxg) {
                best_maxg = mg;
                best_a = "left";
            }
        }
        cout << best_a << endl;
        bool tmp[101][101][4] = {0};
        if (best_a == "step") {
            for (int i = 0; i < R; i++) {
                for (int j = 0; j < C; j++) {
                    for (int dd = 0; dd < 4; dd++) {
                        if (poss[i][j][dd]) {
                            int ni = i + DX[dd];
                            int nj = j + DY[dd];
                            tmp[ni][nj][dd] = true;
                        }
                    }
                }
            }
        } else if (best_a == "left") {
            for (int i = 0; i < R; i++) {
                for (int j = 0; j < C; j++) {
                    for (int dd = 0; dd < 4; dd++) {
                        if (poss[i][j][dd]) {
                            int ndd = (dd + 3) % 4;
                            tmp[i][j][ndd] = true;
                        }
                    }
                }
            }
        } else {
            for (int i = 0; i < R; i++) {
                for (int j = 0; j < C; j++) {
                    for (int dd = 0; dd < 4; dd++) {
                        if (poss[i][j][dd]) {
                            int ndd = (dd + 1) % 4;
                            tmp[i][j][ndd] = true;
                        }
                    }
                }
            }
        }
        memcpy(poss, tmp, sizeof(poss));
    }
    return 0;
}