#include <bits/stdc++.h>
using namespace std;

struct City {
    int id, x, n;
    vector<int> ys;
};

double get_best_cost(bool inc, int& bestp, int& bestq, const vector<City>& cities, double a, double b, int M) {
    const double INF = 1e100;
    vector<int> vorder(M);
    if (inc) {
        iota(vorder.begin(), vorder.end(), 0);
    } else {
        for (int i = 0; i < M; i++) vorder[i] = M - 1 - i;
    }
    vector<double> hz(M - 1, 0.0);
    for (int i = 0; i < M - 1; i++) {
        int c1 = vorder[i], c2 = vorder[i + 1];
        hz[i] = abs(cities[c1].x - cities[c2].x) * 1.0;
    }
    double hret = abs(cities[vorder[M - 1]].x - cities[vorder[0]].x) * 1.0;
    int fidx = vorder[0];
    int lidx = vorder[M - 1];
    int ns = cities[fidx].n;
    int nl = cities[lidx].n;
    double lbest = INF;
    int lp = -1, lq = -1;
    for (int p = 0; p < ns; p++) {
        vector<vector<double>> dpp(M, vector<double>(20, INF));
        dpp[0][p] = 0.0;
        for (int pos = 1; pos < M; pos++) {
            int ccur = vorder[pos];
            int cpre = vorder[pos - 1];
            double hh = hz[pos - 1];
            int nc = cities[ccur].n;
            int np = cities[cpre].n;
            for (int j = 0; j < nc; j++) {
                double mv = INF;
                for (int k = 0; k < np; k++) {
                    double dval = dpp[pos - 1][k];
                    if (dval > INF / 2) continue;
                    int yaa = cities[cpre].ys[k];
                    int ybb = cities[ccur].ys[j];
                    double dyv = ybb - yaa;
                    double distv = sqrt(hh * hh + dyv * dyv);
                    double slopev = (hh > 1e-9 ? (dyv > 0 ? dyv / hh : 0.0) : (dyv > 0 ? 1e9 : 0.0));
                    double adv = a * distv + b * slopev;
                    double tv = dval + adv;
                    mv = min(mv, tv);
                }
                dpp[pos][j] = mv;
            }
        }
        double pb = INF;
        int pq = -1;
        for (int q = 0; q < nl; q++) {
            double dval = dpp[M - 1][q];
            if (dval > INF / 2) continue;
            int yaa = cities[lidx].ys[q];
            int ybb = cities[fidx].ys[p];
            double dyv = ybb - yaa;
            double distv = sqrt(hret * hret + dyv * dyv);
            double slopev = (hret > 1e-9 ? (dyv > 0 ? dyv / hret : 0.0) : (dyv > 0 ? 1e9 : 0.0));
            double adv = a * distv + b * slopev;
            double tv = dval + adv;
            if (tv < pb) {
                pb = tv;
                pq = q;
            }
        }
        if (pb < lbest) {
            lbest = pb;
            lp = p;
            lq = pq;
        }
    }
    bestp = lp;
    bestq = lq;
    return lbest;
}

int main() {
    const double INF = 1e100;
    int M;
    cin >> M;
    vector<City> cities(M);
    for (int i = 0; i < M; i++) {
        int n, x;
        cin >> n >> x;
        cities[i].n = n;
        cities[i].x = x;
        cities[i].ys.resize(n);
        for (int j = 0; j < n; j++) cin >> cities[i].ys[j];
        cities[i].id = i + 1;
    }
    int D_in, S_in;
    cin >> D_in >> S_in;
    double DD = D_in, SS = S_in;
    double aa = 0.4 / DD;
    double bb = 0.6 / SS;
    sort(cities.begin(), cities.end(), [](const City& c1, const City& c2) {
        return c1.x < c2.x;
    });
    int p1, q1;
    double c1 = get_best_cost(true, p1, q1, cities, aa, bb, M);
    int p2, q2;
    double c2 = get_best_cost(false, p2, q2, cities, aa, bb, M);
    bool useinc = (c1 <= c2);
    int bp = useinc ? p1 : p2;
    int bq = useinc ? q1 : q2;
    vector<int> vorder(M);
    if (useinc) {
        iota(vorder.begin(), vorder.end(), 0);
    } else {
        for (int i = 0; i < M; i++) vorder[i] = M - 1 - i;
    }
    vector<double> hz(M - 1);
    for (int i = 0; i < M - 1; i++) {
        hz[i] = abs(cities[vorder[i]].x - cities[vorder[i + 1]].x) * 1.0;
    }
    double hret = abs(cities[vorder[M - 1]].x - cities[vorder[0]].x) * 1.0;
    int fidx = vorder[0];
    int lidx = vorder[M - 1];
    vector<vector<double>> dpp(M, vector<double>(20, INF));
    vector<vector<int>> prevch(M, vector<int>(20, -1));
    dpp[0][bp] = 0.0;
    for (int pos = 1; pos < M; pos++) {
        int ccur = vorder[pos];
        int cpre = vorder[pos - 1];
        double hh = hz[pos - 1];
        int nc = cities[ccur].n;
        int np = cities[cpre].n;
        for (int j = 0; j < nc; j++) {
            double mv = INF;
            int bk = -1;
            for (int k = 0; k < np; k++) {
                double dval = dpp[pos - 1][k];
                if (dval > INF / 2) continue;
                int yaa = cities[cpre].ys[k];
                int ybb = cities[ccur].ys[j];
                double dyv = ybb - yaa;
                double distv = sqrt(hh * hh + dyv * dyv);
                double slopev = (hh > 1e-9 ? (dyv > 0 ? dyv / hh : 0.0) : (dyv > 0 ? 1e9 : 0.0));
                double adv = aa * distv + bb * slopev;
                double tv = dval + adv;
                if (tv < mv) {
                    mv = tv;
                    bk = k;
                }
            }
            dpp[pos][j] = mv;
            prevch[pos][j] = bk;
        }
    }
    vector<int> chosen(M);
    chosen[M - 1] = bq;
    for (int pos = M - 1; pos > 0; pos--) {
        int jj = chosen[pos];
        int kk = prevch[pos][jj];
        chosen[pos - 1] = kk;
    }
    for (int i = 0; i < M; i++) {
        if (i > 0) cout << "@";
        int cidx = vorder[i];
        cout << "(" << cities[cidx].id << "," << chosen[i] + 1 << ")";
    }
    cout << endl;
    return 0;
}