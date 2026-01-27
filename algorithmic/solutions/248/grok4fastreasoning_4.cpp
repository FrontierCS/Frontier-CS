#include <bits/stdc++.h>
using namespace std;

struct City {
    int id, x;
    vector<int> ys;
};

double compute_cost(int x1, int y1, int x2, int y2, double A, double B) {
    double dx = x2 - x1;
    double dy = y2 - y1;
    double hdiff = fabs(dx);
    double dist = sqrt(dx * dx + dy * dy);
    double slope = 0.0;
    if (dy > 0) {
        if (hdiff == 0) {
            slope = 1e9;
        } else {
            slope = dy / hdiff;
        }
    }
    return dist * A + slope * B;
}

int main() {
    double base;
    cin >> base;
    int M;
    cin >> M;
    vector<City> ordered_cities(M);
    for (int i = 0; i < M; i++) {
        int n;
        cin >> n >> ordered_cities[i].x;
        ordered_cities[i].id = i + 1;
        ordered_cities[i].ys.resize(n);
        for (int j = 0; j < n; j++) {
            cin >> ordered_cities[i].ys[j];
        }
    }
    sort(ordered_cities.begin(), ordered_cities.end(), [](const City& a, const City& b) {
        return a.x < b.x;
    });
    int D, S;
    cin >> D >> S;
    double kk = 0.6;
    double AA = (1 - kk) / D;
    double BB = kk / S;
    vector<int> ns(M);
    for (int i = 0; i < M; i++) ns[i] = ordered_cities[i].ys.size();
    double min_cost = 1e100;
    vector<int> best_choices(M, -1);
    for (int p0 = 0; p0 < ns[0]; p0++) {
        int y0 = ordered_cities[0].ys[p0];
        vector<vector<double>> mincost(M);
        vector<vector<int>> prevp(M);
        if (M >= 2) {
            int c1 = 1;
            mincost[1].resize(ns[1]);
            prevp[1].resize(ns[1], -1);
            for (int j = 0; j < ns[1]; j++) {
                int y1 = ordered_cities[1].ys[j];
                double ec = compute_cost(ordered_cities[0].x, y0, ordered_cities[1].x, y1, AA, BB);
                mincost[1][j] = ec;
            }
            for (int ci = 2; ci < M; ci++) {
                mincost[ci].resize(ns[ci]);
                prevp[ci].resize(ns[ci], -1);
                for (int j = 0; j < ns[ci]; j++) {
                    int yi = ordered_cities[ci].ys[j];
                    double bestv = 1e100;
                    int bestprev = -1;
                    for (int pk = 0; pk < ns[ci - 1]; pk++) {
                        int yprev = ordered_cities[ci - 1].ys[pk];
                        double ec = compute_cost(ordered_cities[ci - 1].x, yprev, ordered_cities[ci].x, yi, AA, BB);
                        double totv = mincost[ci - 1][pk] + ec;
                        if (totv < bestv) {
                            bestv = totv;
                            bestprev = pk;
                        }
                    }
                    mincost[ci][j] = bestv;
                    prevp[ci][j] = bestprev;
                }
            }
        }
        double this_min = 1e100;
        int best_last = -1;
        for (int j = 0; j < ns[M - 1]; j++) {
            int yl = ordered_cities[M - 1].ys[j];
            double ec_ret = compute_cost(ordered_cities[M - 1].x, yl, ordered_cities[0].x, y0, AA, BB);
            double tot = 0.0;
            if (M >= 2) {
                tot = mincost[M - 1][j] + ec_ret;
            } else {
                tot = ec_ret;
            }
            if (tot < this_min) {
                this_min = tot;
                best_last = j;
            }
        }
        if (this_min < min_cost) {
            min_cost = this_min;
            vector<int> ch(M);
            ch[M - 1] = best_last;
            int cur_ci = M - 1;
            int cur_pj = best_last;
            while (cur_ci > 1) {
                int pr = prevp[cur_ci][cur_pj];
                ch[cur_ci - 1] = pr;
                cur_pj = pr;
                cur_ci--;
            }
            if (M >= 2) {
                ch[1] = cur_pj;
            }
            ch[0] = p0;
            best_choices = ch;
        }
    }
    for (int i = 0; i < M; i++) {
        if (i > 0) cout << "@";
        cout << "(" << ordered_cities[i].id << "," << best_choices[i] + 1 << ")";
    }
    cout << endl;
    return 0;
}