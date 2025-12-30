#include <bits/stdc++.h>
using namespace std;

int main() {
    srand(time(NULL));
    vector<vector<int>> orig(30, vector<int>(30));
    for (int i = 0; i < 30; i++) {
        string s;
        cin >> s;
        for (int j = 0; j < 30; j++) {
            orig[i][j] = s[j] - '0';
        }
    }
    int to[8][4] = {
        {1, 0, -1, -1},
        {3, -1, -1, 0},
        {-1, -1, 3, 2},
        {-1, 2, 1, -1},
        {1, 0, 3, 2},
        {3, 2, 1, 0},
        {2, -1, 0, -1},
        {-1, 3, -1, 1}
    };
    int dx[4] = {0, -1, 0, 1};
    int dy[4] = {-1, 0, 1, 0};
    int eff_type[8][4];
    for (int o = 0; o < 8; o++) {
        for (int ro = 0; ro < 4; ro++) {
            int t = o;
            for (int k = 0; k < ro; k++) {
                if (t < 4) {
                    t = (t + 1) % 4;
                } else if (t < 6) {
                    t = (t == 4 ? 5 : 4);
                } else {
                    t = (t == 6 ? 7 : 6);
                }
            }
            eff_type[o][ro] = t;
        }
    }
    vector<vector<int>> best_r(30, vector<int>(30, 0));
    long long best_score = 0;
    const int TRIALS = 10000;
    for (int trial = 0; trial < TRIALS; trial++) {
        vector<vector<int>> curr_r(30, vector<int>(30));
        for (int i = 0; i < 30; i++) {
            for (int j = 0; j < 30; j++) {
                curr_r[i][j] = rand() % 4;
            }
        }
        vector<vector<int>> tiles(30, vector<int>(30));
        for (int i = 0; i < 30; i++) {
            for (int j = 0; j < 30; j++) {
                tiles[i][j] = eff_type[orig[i][j]][curr_r[i][j]];
            }
        }
        vector<int> nextn(3600, -1);
        for (int i = 0; i < 30; i++) {
            for (int j = 0; j < 30; j++) {
                for (int d = 0; d < 4; d++) {
                    int t = tiles[i][j];
                    if (to[t][d] == -1) continue;
                    int id = ((i * 30 + j) * 4 + d);
                    int d2 = to[t][d];
                    int ni = i + dx[d2];
                    int nj = j + dy[d2];
                    if (ni < 0 || ni >= 30 || nj < 0 || nj >= 30) continue;
                    int nd = (d2 + 2) % 4;
                    int nt = tiles[ni][nj];
                    if (to[nt][nd] == -1) continue;
                    int nid = ((ni * 30 + nj) * 4 + nd);
                    nextn[id] = nid;
                }
            }
        }
        vector<bool> visited(3600, false);
        vector<int> cycle_lengths;
        vector<int> pathh;
        for (int i = 0; i < 30; i++) {
            for (int j = 0; j < 30; j++) {
                for (int d = 0; d < 4; d++) {
                    int id = ((i * 30 + j) * 4 + d);
                    int t = tiles[i][j];
                    if (to[t][d] == -1) continue;
                    if (visited[id]) continue;
                    pathh.clear();
                    int cur = id;
                    while (!visited[cur] && nextn[cur] != -1) {
                        visited[cur] = true;
                        pathh.push_back(cur);
                        cur = nextn[cur];
                    }
                    if (cur != -1 && visited[cur]) {
                        auto it = find(pathh.begin(), pathh.end(), cur);
                        if (it != pathh.end()) {
                            size_t idx = it - pathh.begin();
                            int clen = pathh.size() - idx;
                            if (clen >= 2) {
                                cycle_lengths.push_back(clen);
                            }
                        }
                    }
                }
            }
        }
        map<int, int> cnt;
        for (int l : cycle_lengths) cnt[l]++;
        vector<int> loops;
        for (auto& p : cnt) {
            int num = p.second / 2;
            for (int k = 0; k < num; k++) {
                loops.push_back(p.first);
            }
        }
        sort(loops.rbegin(), loops.rend());
        long long sc = 0;
        if (loops.size() >= 2) {
            sc = 1LL * loops[0] * loops[1];
        }
        if (sc > best_score) {
            best_score = sc;
            best_r = curr_r;
        }
    }
    for (int i = 0; i < 30; i++) {
        for (int j = 0; j < 30; j++) {
            cout << best_r[i][j];
        }
    }
    cout << endl;
    return 0;
}