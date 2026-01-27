#include <bits/stdc++.h>
using namespace std;

struct City {
    int id, x, n;
    vector<int> ys;
};

double compute_cost(const vector<City>& sc, const vector<vector<int>>& all_ys, int pa, int ja, int pb, int jb, double DD, double SS) {
    double dx = (double)sc[pa].x - (double)sc[pb].x;
    double horiz = fabs(dx);
    int ya = all_ys[pa][ja];
    int yb = all_ys[pb][jb];
    double dy = (double)yb - (double)ya;
    double dist = sqrt(dx * dx + dy * dy);
    double climb = 0.0;
    if (dy > 0) {
        if (horiz < 1e-9) {
            climb = 1e18;
        } else {
            climb = dy / horiz;
        }
    }
    return dist * DD + climb * SS;
}

int main() {
    double base;
    cin >> base;
    int M;
    cin >> M;
    vector<City> cities(M);
    for (int i = 0; i < M; i++) {
        int nn, xx;
        cin >> nn >> xx;
        cities[i].n = nn;
        cities[i].x = xx;
        cities[i].id = i + 1;
        cities[i].ys.resize(nn);
        for (int& y : cities[i].ys) cin >> y;
    }
    double DD, SS;
    cin >> DD >> SS;
    const double INF = 1e30;
    const int MAXN = 21;
    auto compute = [&](bool ascending) -> pair<double, vector<pair<int, int>>> {
        vector<City> sc = cities;
        if (ascending) {
            sort(sc.begin(), sc.end(), [](const City& a, const City& b) { return a.x < b.x; });
        } else {
            sort(sc.begin(), sc.end(), [](const City& a, const City& b) { return a.x > b.x; });
        }
        vector<vector<int>> all_ys(M);
        vector<int> ns(M);
        for (int p = 0; p < M; p++) {
            all_ys[p] = sc[p].ys;
            ns[p] = (int)all_ys[p].size();
        }
        int n0 = ns[0];
        vector<vector<double>> path_costs(MAXN, vector<double>(MAXN, INF));
        vector<vector<vector<int>>> prev_all(MAXN);
        double global_min = INF;
        int best_sk_local = -1, best_lj_local = -1;
        for (int sk = 0; sk < n0; sk++) {
            vector<vector<double>> dp(M, vector<double>(MAXN, INF));
            vector<vector<int>> prev(M, vector<int>(MAXN, -1));
            dp[0][sk] = 0.0;
            for (int i = 1; i < M; i++) {
                for (int j = 0; j < ns[i]; j++) {
                    double minv = INF;
                    int bestp = -1;
                    for (int p = 0; p < ns[i - 1]; p++) {
                        if (dp[i - 1][p] >= INF) continue;
                        double c = compute_cost(sc, all_ys, i - 1, p, i, j, DD, SS);
                        double tot = dp[i - 1][p] + c;
                        if (tot < minv) {
                            minv = tot;
                            bestp = p;
                        }
                    }
                    if (bestp != -1) {
                        dp[i][j] = minv;
                        prev[i][j] = bestp;
                    }
                }
            }
            prev_all[sk] = prev;
            for (int j = 0; j < ns[M - 1]; j++) {
                path_costs[sk][j] = dp[M - 1][j];
            }
            for (int lj = 0; lj < ns[M - 1]; lj++) {
                if (path_costs[sk][lj] >= INF) continue;
                double closing = compute_cost(sc, all_ys, M - 1, lj, 0, sk, DD, SS);
                double total = path_costs[sk][lj] + closing;
                if (total < global_min) {
                    global_min = total;
                    best_sk_local = sk;
                    best_lj_local = lj;
                }
            }
        }
        vector<int> choices(M, -1);
        choices[0] = best_sk_local;
        int curr_i = M - 1;
        int curr_j = best_lj_local;
        choices[M - 1] = curr_j;
        auto& this_prev = prev_all[best_sk_local];
        for (int i = M - 1; i >= 1; i--) {
            int pre_j = this_prev[i][curr_j];
            choices[i - 1] = pre_j;
            curr_j = pre_j;
        }
        vector<pair<int, int>> sequence;
        for (int p = 0; p < M; p++) {
            int cid = sc[p].id;
            int pidx = choices[p] + 1;
            sequence.emplace_back(cid, pidx);
        }
        return {global_min, sequence};
    };
    auto [cost_asc, seq_asc] = compute(true);
    auto [cost_desc, seq_desc] = compute(false);
    bool use_asc = (cost_asc <= cost_desc);
    auto& seq = use_asc ? seq_asc : seq_desc;
    for (int i = 0; i < M; i++) {
        auto [cid, pidx] = seq[i];
        cout << "(" << cid << "," << pidx << ")";
        if (i < M - 1) cout << "@";
    }
    cout << endl;
    return 0;
}