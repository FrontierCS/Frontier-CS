#include <bits/stdc++.h>
using namespace std;

struct City {
    int id, x;
    vector<int> ys;
};

double get_cost(int i1, int p1, int i2, int p2, const vector<City>& cc, double DD, double SS) {
    double x1 = cc[i1].x;
    double x2 = cc[i2].x;
    double dx = fabs(x1 - x2);
    if (dx == 0.0) return 1e9;
    double y1 = cc[i1].ys[p1];
    double y2 = cc[i2].ys[p2];
    double dy = y2 - y1;
    double dist = sqrt(dx * dx + dy * dy);
    double slp = (dy > 0 ? dy / dx : 0.0);
    double res = 0.4 / DD * dist + 0.6 / SS * slp;
    return res;
}

pair<double, vector<int>> compute_cycle(const vector<City>& cc, double D, double S) {
    int M = cc.size();
    if (M == 0) return {0.0, {}};
    double min_c = 1e100;
    int best_s = -1;
    int best_t = -1;
    int maxn = 0;
    for (auto& ci : cc) maxn = max(maxn, (int)ci.ys.size());
    for (int s = 0; s < (int)cc[0].ys.size(); ++s) {
        vector<vector<double>> dp(M, vector<double>(maxn, 1e100));
        dp[0][s] = 0.0;
        for (int pos = 1; pos < M; ++pos) {
            int n_prev = cc[pos - 1].ys.size();
            int n_cur = cc[pos].ys.size();
            for (int j = 0; j < n_cur; ++j) {
                double minv = 1e100;
                for (int k = 0; k < n_prev; ++k) {
                    if (dp[pos - 1][k] > 1e99) continue;
                    double cst = get_cost(pos - 1, k, pos, j, cc, D, S);
                    double tot = dp[pos - 1][k] + cst;
                    if (tot < minv) {
                        minv = tot;
                    }
                }
                dp[pos][j] = minv;
            }
        }
        int n_last = cc[M - 1].ys.size();
        for (int t = 0; t < n_last; ++t) {
            if (dp[M - 1][t] > 1e99) continue;
            double cst = get_cost(M - 1, t, 0, s, cc, D, S);
            double tot = dp[M - 1][t] + cst;
            if (tot < min_c) {
                min_c = tot;
                best_s = s;
                best_t = t;
            }
        }
    }
    // Rerun for best_s to get predecessors
    vector<vector<double>> dp(M, vector<double>(maxn, 1e100));
    vector<vector<int>> pre(M, vector<int>(maxn, -1));
    dp[0][best_s] = 0.0;
    for (int pos = 1; pos < M; ++pos) {
        int n_prev = cc[pos - 1].ys.size();
        int n_cur = cc[pos].ys.size();
        for (int j = 0; j < n_cur; ++j) {
            double minv = 1e100;
            int bestk = -1;
            for (int k = 0; k < n_prev; ++k) {
                if (dp[pos - 1][k] > 1e99) continue;
                double cst = get_cost(pos - 1, k, pos, j, cc, D, S);
                double tot = dp[pos - 1][k] + cst;
                if (tot < minv) {
                    minv = tot;
                    bestk = k;
                }
            }
            dp[pos][j] = minv;
            pre[pos][j] = bestk;
        }
    }
    // Backtrack
    vector<int> chosen(M, -1);
    chosen[0] = best_s;
    int cur_pos = M - 1;
    int cur_p = best_t;
    chosen[cur_pos] = cur_p;
    while (cur_pos > 0) {
        int pre_p = pre[cur_pos][cur_p];
        --cur_pos;
        chosen[cur_pos] = pre_p;
        cur_p = pre_p;
    }
    return {min_c, chosen};
}

int main() {
    double base;
    cin >> base;
    int M;
    cin >> M;
    vector<City> cities(M);
    for (int i = 0; i < M; ++i) {
        int n, x;
        cin >> n >> x;
        cities[i].id = i + 1;
        cities[i].x = x;
        cities[i].ys.resize(n);
        for (int j = 0; j < n; ++j) {
            cin >> cities[i].ys[j];
        }
    }
    double D, S;
    cin >> D >> S;
    vector<City> sorted_c = cities;
    sort(sorted_c.begin(), sorted_c.end(), [](const City& a, const City& b) {
        return a.x < b.x;
    });
    auto [cost1, chosen1] = compute_cycle(sorted_c, D, S);
    vector<City> rev_c = sorted_c;
    reverse(rev_c.begin(), rev_c.end());
    auto [cost2, chosen2] = compute_cycle(rev_c, D, S);
    bool use_forward = (cost1 <= cost2);
    const vector<City>& best_c = use_forward ? sorted_c : rev_c;
    const vector<int>& best_chosen = use_forward ? chosen1 : chosen2;
    // Build route
    vector<pair<int, int>> route;
    for (int i = 0; i < M; ++i) {
        int cid = best_c[i].id;
        int pidx = best_chosen[i] + 1;
        route.emplace_back(cid, pidx);
    }
    // Rotate to start with smallest city id
    int min_id_pos = 0;
    int min_id = route[0].first;
    for (int i = 1; i < M; ++i) {
        if (route[i].first < min_id) {
            min_id = route[i].first;
            min_id_pos = i;
        }
    }
    vector<pair<int, int>> final_route;
    for (int i = 0; i < M; ++i) {
        final_route.push_back(route[(i + min_id_pos) % M]);
    }
    // Output
    for (int i = 0; i < M; ++i) {
        if (i > 0) cout << "@";
        auto [cid, p] = final_route[i];
        cout << "(" << cid << "," << p << ")";
    }
    cout << endl;
    return 0;
}