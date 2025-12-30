#include <bits/stdc++.h>
using namespace std;

int main() {
    int si, sj, ti, tj;
    double p;
    cin >> si >> sj >> ti >> tj >> p;
    vector<string> H(20);
    for (int i = 0; i < 20; i++) cin >> H[i];
    vector<string> V(19);
    for (int i = 0; i < 19; i++) cin >> V[i];

    int dr[4] = {-1, 1, 0, 0};
    int dc[4] = {0, 0, -1, 1};
    char chs[4] = {'U', 'D', 'L', 'R'};

    auto can_move = [&](int r, int c, int a) -> bool {
        int nr = r + dr[a];
        int nc = c + dc[a];
        if (nr < 0 || nr >= 20 || nc < 0 || nc >= 20) return false;
        if (a == 0) return V[nr][nc] == '0';
        if (a == 1) return V[r][nc] == '0';
        if (a == 2) return H[r][nc] == '0';
        return H[r][c] == '0';
    };

    auto is_target = [&](int r, int c) { return r == ti && c == tj; };
    auto idx = [&](int r, int c) { return r * 20 + c; };

    const int MAX_T = 200;
    const int N = 20;
    double f[202][20][20];
    int best_act[202][20][20];
    memset(f, 0, sizeof(f));
    memset(best_act, 0, sizeof(best_act));

    for (int tau = MAX_T; tau >= 1; tau--) {
        for (int r = 0; r < N; r++) {
            for (int c = 0; c < N; c++) {
                if (is_target(r, c)) continue;
                double best_exp = 0.0;
                int ba = 0;
                for (int a = 0; a < 4; a++) {
                    double expv = 0.0;
                    // stay
                    {
                        int sr = r, sc = c;
                        double ps = p;
                        if (is_target(sr, sc)) {
                            expv += ps * (401.0 - tau);
                        } else {
                            expv += ps * f[tau + 1][sr][sc];
                        }
                    }
                    // move
                    {
                        int nr = r + dr[a];
                        int nc = c + dc[a];
                        bool can = can_move(r, c, a);
                        int mr = can ? nr : r;
                        int mc = can ? nc : c;
                        double pm = 1.0 - p;
                        if (is_target(mr, mc)) {
                            expv += pm * (401.0 - tau);
                        } else {
                            expv += pm * f[tau + 1][mr][mc];
                        }
                    }
                    if (expv > best_exp + 1e-9) {
                        best_exp = expv;
                        ba = a;
                    }
                }
                f[tau][r][c] = best_exp;
                best_act[tau][r][c] = ba;
            }
        }
    }

    struct Item {
        string path;
        vector<double> dist;
        double cum_E;
        double score;
    };

    int B = 20;
    vector<Item> beam(1);
    beam[0].path = "";
    beam[0].dist.assign(400, 0.0);
    int start_idx = idx(si, sj);
    beam[0].dist[start_idx] = 1.0;
    beam[0].cum_E = 0.0;
    double init_fut = 0.0;
    int sr0 = si, sc0 = sj;
    if (!is_target(sr0, sc0)) init_fut = f[1][sr0][sc0];
    beam[0].score = init_fut;

    for (int len = 1; len <= MAX_T; len++) {
        vector<Item> newb;
        for (const auto& it : beam) {
            for (int a = 0; a < 4; a++) {
                char ch = chs[a];
                double arrive_now = 0.0;
                vector<double> newd(400, 0.0);
                for (int i = 0; i < 400; i++) {
                    if (it.dist[i] < 1e-12) continue;
                    double pr = it.dist[i];
                    int r = i / 20;
                    int c = i % 20;
                    // forget
                    {
                        int sr = r, sc = c;
                        double ps = p * pr;
                        if (is_target(sr, sc)) {
                            arrive_now += ps;
                        } else {
                            newd[idx(sr, sc)] += ps;
                        }
                    }
                    // move
                    {
                        int nr = r + dr[a];
                        int nc = c + dc[a];
                        bool can = can_move(r, c, a);
                        int mr = can ? nr : r;
                        int mc = can ? nc : c;
                        double pm = (1.0 - p) * pr;
                        if (is_target(mr, mc)) {
                            arrive_now += pm;
                        } else {
                            newd[idx(mr, mc)] += pm;
                        }
                    }
                }
                double new_cum = it.cum_E + arrive_now * (401.0 - len);
                double fut = 0.0;
                for (int i = 0; i < 400; i++) {
                    if (newd[i] < 1e-12) continue;
                    int r = i / 20;
                    int c = i % 20;
                    if (is_target(r, c)) continue;
                    fut += newd[i] * f[len + 1][r][c];
                }
                double this_score = new_cum + fut;
                Item ni;
                ni.path = it.path + ch;
                ni.dist = newd;
                ni.cum_E = new_cum;
                ni.score = this_score;
                newb.push_back(ni);
            }
        }
        sort(newb.begin(), newb.end(), [](const Item& x, const Item& y) {
            return x.score > y.score;
        });
        int take = min((int)newb.size(), B);
        beam.clear();
        beam.reserve(take);
        for (int i = 0; i < take; i++) {
            beam.push_back(newb[i]);
        }
    }

    cout << beam[0].path << endl;
    return 0;
}