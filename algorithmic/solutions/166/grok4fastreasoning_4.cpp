#include <bits/stdc++.h>
using namespace std;

int main() {
    int N = 20;
    vector<vector<int>> supply(N, vector<int>(N, 0));
    vector<vector<int>> demand(N, vector<int>(N, 0));
    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            int h;
            cin >> h;
            if (h > 0) {
                supply[i][j] = h;
            } else {
                demand[i][j] = -h;
            }
        }
    }
    int cr = 0, cc = 0;
    int cload = 0;
    vector<string> ops;
    const int INF = 1e9 + 5;
    while (true) {
        bool alldone = true;
        for (int i = 0; i < N; i++) {
            for (int j = 0; j < N; j++) {
                if (supply[i][j] > 0 || demand[i][j] > 0) {
                    alldone = false;
                }
            }
        }
        if (alldone && cload == 0) break;
        if (cload > 0) {
            int min_d = INF;
            int tr = -1, tc = -1;
            int maxdem = 0;
            for (int i = 0; i < N; i++) {
                for (int j = 0; j < N; j++) {
                    if (demand[i][j] > 0) {
                        int dist = abs(i - cr) + abs(j - cc);
                        if (dist < min_d || (dist == min_d && demand[i][j] > maxdem)) {
                            min_d = dist;
                            tr = i;
                            tc = j;
                            maxdem = demand[i][j];
                        }
                    }
                }
            }
            if (tr == -1) break;
            int dr = tr - cr;
            int dc = tc - cc;
            if (dc > 0) {
                for (int k = 0; k < dc; k++) ops.push_back("R");
            } else if (dc < 0) {
                for (int k = 0; k < -dc; k++) ops.push_back("L");
            }
            if (dr > 0) {
                for (int k = 0; k < dr; k++) ops.push_back("D");
            } else if (dr < 0) {
                for (int k = 0; k < -dr; k++) ops.push_back("U");
            }
            cr = tr;
            cc = tc;
            int dd = min(cload, demand[cr][cc]);
            ops.push_back("-" + to_string(dd));
            cload -= dd;
            demand[cr][cc] -= dd;
        } else {
            int min_d = INF;
            int tr = -1, tc = -1;
            int maxsup = 0;
            for (int i = 0; i < N; i++) {
                for (int j = 0; j < N; j++) {
                    if (supply[i][j] > 0) {
                        int dist = abs(i - cr) + abs(j - cc);
                        if (dist < min_d || (dist == min_d && supply[i][j] > maxsup)) {
                            min_d = dist;
                            tr = i;
                            tc = j;
                            maxsup = supply[i][j];
                        }
                    }
                }
            }
            if (tr == -1) break;
            int dr = tr - cr;
            int dc = tc - cc;
            if (dc > 0) {
                for (int k = 0; k < dc; k++) ops.push_back("R");
            } else if (dc < 0) {
                for (int k = 0; k < -dc; k++) ops.push_back("L");
            }
            if (dr > 0) {
                for (int k = 0; k < dr; k++) ops.push_back("D");
            } else if (dr < 0) {
                for (int k = 0; k < -dr; k++) ops.push_back("U");
            }
            cr = tr;
            cc = tc;
            int dd = supply[cr][cc];
            ops.push_back("+" + to_string(dd));
            cload += dd;
            supply[cr][cc] = 0;
        }
    }
    for (auto &s : ops) {
        cout << s << '\n';
    }
    return 0;
}