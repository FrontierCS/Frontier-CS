#include <bits/stdc++.h>
using namespace std;

struct Pos {
    int x, y;
};

int main() {
    int si, sj, ti, tj;
    double pp;
    cin >> si >> sj >> ti >> tj >> pp;
    double p = pp;
    vector<string> hh(20);
    for (auto &s : hh) cin >> s;
    vector<string> vv(19);
    for (auto &s : vv) cin >> s;
    vector<vector<bool>> hor_wall(20, vector<bool>(19, false));
    vector<vector<bool>> ver_wall(19, vector<bool>(20, false));
    for (int i = 0; i < 20; i++) {
        for (int j = 0; j < 19; j++) {
            hor_wall[i][j] = (hh[i][j] == '1');
        }
    }
    for (int i = 0; i < 19; i++) {
        for (int j = 0; j < 20; j++) {
            ver_wall[i][j] = (vv[i][j] == '1');
        }
    }
    if (si == ti && sj == tj) {
        cout << "" << endl;
        return 0;
    }
    // Compute dist_to target
    vector<vector<int>> dist_to(20, vector<int>(20, -1));
    queue<Pos> qq;
    qq.push({ti, tj});
    dist_to[ti][tj] = 0;
    while (!qq.empty()) {
        Pos cur = qq.front(); qq.pop();
        int x = cur.x, y = cur.y;
        for (char dir : string("UDLR")) {
            int nx = x, ny = y;
            if (dir == 'U' && x > 0 && !ver_wall[x - 1][y]) nx = x - 1;
            else if (dir == 'D' && x < 19 && !ver_wall[x][y]) nx = x + 1;
            else if (dir == 'L' && y > 0 && !hor_wall[x][y - 1]) ny = y - 1;
            else if (dir == 'R' && y < 19 && !hor_wall[x][y]) ny = y + 1;
            if (dist_to[nx][ny] == -1) {
                dist_to[nx][ny] = dist_to[x][y] + 1;
                qq.push({nx, ny});
            }
        }
    }
    for (int i = 0; i < 20; i++) {
        for (int j = 0; j < 20; j++) {
            if (dist_to[i][j] == -1) dist_to[i][j] = 100;
        }
    }
    // Greedy construction
    vector<vector<double>> current_prob(20, vector<double>(20, 0.0));
    current_prob[si][sj] = 1.0;
    string ans = "";
    for (int l = 1; l <= 200; l++) {
        double unfinished = 0.0;
        for (int x = 0; x < 20; x++) {
            for (int y = 0; y < 20; y++) {
                unfinished += current_prob[x][y];
            }
        }
        if (unfinished < 1e-9) break;
        double max_est = -1e100;
        char best_c = 'U';
        vector<vector<double>> best_prob(20, vector<double>(20, 0.0));
        double best_newc = -1.0;
        for (char cc : string("UDLR")) {
            double new_contrib = 0.0;
            vector<vector<double>> temp(20, vector<double>(20, 0.0));
            bool all_zero = true;
            for (int x = 0; x < 20; x++) {
                for (int y = 0; y < 20; y++) {
                    double pr = current_prob[x][y];
                    if (pr < 1e-12) continue;
                    all_zero = false;
                    // stay
                    {
                        double ps = p * pr;
                        int nsx = x, nsy = y;
                        if (nsx == ti && nsy == tj) {
                            new_contrib += ps * (401.0 - l);
                        } else {
                            temp[nsx][nsy] += ps;
                        }
                    }
                    // move
                    {
                        double pm = (1.0 - p) * pr;
                        int mx = x, my = y;
                        if (cc == 'U' && x > 0 && !ver_wall[x - 1][y]) {
                            mx = x - 1;
                        } else if (cc == 'D' && x < 19 && !ver_wall[x][y]) {
                            mx = x + 1;
                        } else if (cc == 'L' && y > 0 && !hor_wall[x][y - 1]) {
                            my = y - 1;
                        } else if (cc == 'R' && y < 19 && !hor_wall[x][y]) {
                            my = y + 1;
                        }
                        if (mx == ti && my == tj) {
                            new_contrib += pm * (401.0 - l);
                        } else {
                            temp[mx][my] += pm;
                        }
                    }
                }
            }
            if (all_zero) continue;
            // estimate future
            double est_f = 0.0;
            for (int x = 0; x < 20; x++) {
                for (int y = 0; y < 20; y++) {
                    double pp2 = temp[x][y];
                    if (pp2 > 1e-12) {
                        int d = dist_to[x][y];
                        double val = 401.0 - l - d;
                        if (val > 0) est_f += pp2 * val;
                    }
                }
            }
            double tot = new_contrib + est_f;
            if (tot > max_est + 1e-9 || (abs(tot - max_est) < 1e-9 && new_contrib > best_newc + 1e-9)) {
                max_est = tot;
                best_c = cc;
                best_prob = temp;
                best_newc = new_contrib;
            }
        }
        ans += best_c;
        current_prob = best_prob;
    }
    cout << ans << endl;
    return 0;
}