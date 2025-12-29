#include <bits/stdc++.h>
using namespace std;

int main() {
    int N, M;
    cin >> N >> M;
    int si, sj;
    cin >> si >> sj;
    vector<string> A(N);
    for (int i = 0; i < N; i++) cin >> A[i];
    vector<string> T(M);
    for (int i = 0; i < M; i++) cin >> T[i];
    vector<vector<pair<int, int>>> pos_list(26);
    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            char c = A[i][j];
            pos_list[c - 'A'].emplace_back(i, j);
        }
    }
    const int INF = 0x3f3f3f3f;
    struct WordInfo {
        vector<vector<pair<int, int>>> valid;
        vector<int> internal;
    };
    vector<WordInfo> info(M);
    for (int w = 0; w < M; w++) {
        string t = T[w];
        auto& v = info[w].valid;
        v.resize(5);
        for (int k = 0; k < 5; k++) {
            char c = t[k];
            v[k] = pos_list[c - 'A'];
        }
        auto& inter = info[w].internal;
        int np1 = v[0].size();
        inter.assign(np1, INF);
        for (int p1 = 0; p1 < np1; p1++) {
            auto [i1, j1] = v[0][p1];
            int dp[6][15][15];
            memset(dp, 0x3f, sizeof(dp));
            dp[1][i1][j1] = 0;
            for (int k = 2; k <= 5; k++) {
                char need = t[k - 1];
                auto& cands = pos_list[need - 'A'];
                for (int pi = 0; pi < N; pi++) {
                    for (int pj = 0; pj < N; pj++) {
                        if (dp[k - 1][pi][pj] >= INF) continue;
                        for (auto [ni, nj] : cands) {
                            int d = abs(ni - pi) + abs(nj - pj);
                            int newc = dp[k - 1][pi][pj] + d;
                            if (newc < dp[k][ni][nj]) {
                                dp[k][ni][nj] = newc;
                            }
                        }
                    }
                }
            }
            int min_int = INF;
            for (int i = 0; i < N; i++) {
                for (int j = 0; j < N; j++) {
                    min_int = min(min_int, dp[5][i][j]);
                }
            }
            inter[p1] = min_int;
        }
    }
    vector<bool> covered(M, false);
    pair<int, int> cur = {si, sj};
    vector<pair<int, int>> sequence;
    int num_covered = 0;
    while (num_covered < M) {
        int best_w = -1;
        int best_move = INF;
        int best_p1_idx = -1;
        for (int w = 0; w < M; w++) {
            if (covered[w]) continue;
            auto& v = info[w].valid;
            auto& inter = info[w].internal;
            int np1 = v[0].size();
            int this_min = INF;
            int local_best_p1 = -1;
            for (int p1 = 0; p1 < np1; p1++) {
                auto [i1, j1] = v[0][p1];
                int d = abs(i1 - cur.first) + abs(j1 - cur.second);
                int total_move = d + inter[p1];
                if (total_move < this_min) {
                    this_min = total_move;
                    local_best_p1 = p1;
                }
            }
            if (this_min < best_move) {
                best_move = this_min;
                best_w = w;
                best_p1_idx = local_best_p1;
            }
        }
        int w = best_w;
        int p1_idx = best_p1_idx;
        auto& v = info[w].valid;
        auto pos1 = v[0][p1_idx];
        int i1 = pos1.first, j1 = pos1.second;
        int dp[6][15][15];
        int prev_i[6][15][15];
        int prev_j[6][15][15];
        memset(dp, 0x3f, sizeof(dp));
        memset(prev_i, 0x3f, sizeof(prev_i));
        memset(prev_j, 0x3f, sizeof(prev_j));
        dp[1][i1][j1] = 0;
        for (int k = 2; k <= 5; k++) {
            char need = T[w][k - 1];
            auto& cands = pos_list[need - 'A'];
            for (int pi = 0; pi < N; pi++) {
                for (int pj = 0; pj < N; pj++) {
                    if (dp[k - 1][pi][pj] >= INF) continue;
                    for (auto [ni, nj] : cands) {
                        int d = abs(ni - pi) + abs(nj - pj);
                        int newc = dp[k - 1][pi][pj] + d;
                        if (newc < dp[k][ni][nj]) {
                            dp[k][ni][nj] = newc;
                            prev_i[k][ni][nj] = pi;
                            prev_j[k][ni][nj] = pj;
                        }
                    }
                }
            }
        }
        int min_int_actual = INF;
        int ei = -1, ej = -1;
        for (int i = 0; i < N; i++) {
            for (int j = 0; j < N; j++) {
                if (dp[5][i][j] < min_int_actual) {
                    min_int_actual = dp[5][i][j];
                    ei = i;
                    ej = j;
                }
            }
        }
        vector<pair<int, int>> path;
        pair<int, int> current = {ei, ej};
        path.push_back(current);
        for (int k = 5; k >= 2; k--) {
            int pi = prev_i[k][current.first][current.second];
            int pj = prev_j[k][current.first][current.second];
            current = {pi, pj};
            path.push_back(current);
        }
        reverse(path.begin(), path.end());
        for (auto p : path) {
            sequence.push_back(p);
        }
        cur = path.back();
        covered[w] = true;
        num_covered++;
    }
    for (auto [i, j] : sequence) {
        cout << i << " " << j << "\n";
    }
}