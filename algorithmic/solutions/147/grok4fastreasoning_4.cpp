#include <bits/stdc++.h>
using namespace std;

double get_p(long long r, long long s) {
    if (s == 0) return 0.0;
    long long mn = min(r, s);
    long long mx = max(r, s);
    double ratio = (double)mn / mx;
    return 1.0 - (1.0 - ratio) * (1.0 - ratio);
}

struct Rect {
    int a, b, c, d;
};

struct Cand {
    double p;
    int w, h;
    bool operator>(const Cand& other) const {
        return p > other.p;
    }
};

bool check_valid(int i, int aa, int bb, int cc, int dd, const vector<int>& X, const vector<int>& Y, const vector<Rect>& placed) {
    int n = X.size();
    for (int j = 0; j < n; j++) {
        if (j == i) continue;
        int xj = X[j], yj = Y[j];
        if (aa <= xj && cc >= xj + 1 && bb <= yj && dd >= yj + 1) {
            return false;
        }
    }
    for (const auto& pr : placed) {
        int ap = pr.a, bp = pr.b, cp = pr.c, dp = pr.d;
        if (max(aa, ap) < min(cc, cp) && max(bb, bp) < min(dd, dp)) {
            return false;
        }
    }
    return true;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    cin >> n;
    vector<int> X(n), Y(n);
    vector<long long> R(n);
    for (int i = 0; i < n; i++) {
        cin >> X[i] >> Y[i] >> R[i];
    }
    vector<int> order(n);
    iota(order.begin(), order.end(), 0);
    sort(order.begin(), order.end(), [&](int i, int j) {
        if (R[i] != R[j]) return R[i] > R[j];
        return i < j;
    });
    vector<int> A(n), B(n), C(n), D(n);
    vector<Rect> placed_rects;
    for (int o = 0; o < n; o++) {
        int idx = order[o];
        long long rr = R[idx];
        vector<Cand> cands;
        double sqr = sqrt((double)rr);
        int basew = (int)round(sqr);
        const int K = 50;
        set<pair<int, int>> seen;
        for (int d = -K; d <= K; d++) {
            int ww = basew + d;
            if (ww < 1 || ww > 10000) continue;
            double hd = (double)rr / ww;
            int hh = (int)round(hd);
            if (hh < 1 || hh > 10000) continue;
            long long ss = (long long)ww * hh;
            double pp = get_p(rr, ss);
            int w1 = ww, h1 = hh;
            if (w1 > h1) swap(w1, h1);
            if (seen.count({w1, h1})) continue;
            seen.insert({w1, h1});
            cands.push_back({pp, ww, hh});
            if (ww != hh) {
                cands.push_back({pp, hh, ww});
            }
        }
        sort(cands.begin(), cands.end(), greater<Cand>());
        int num_try = min(10, (int)cands.size());
        bool found = false;
        int x = X[idx], y = Y[idx];
        for (int ci = 0; ci < num_try && !found; ci++) {
            int ww = cands[ci].w;
            int hh = cands[ci].h;
            int low_a = max(0, x + 1 - ww);
            int high_a = min(x, 10000 - ww);
            if (low_a > high_a) continue;
            int low_b = max(0, y + 1 - hh);
            int high_b = min(y, 10000 - hh);
            if (low_b > high_b) continue;
            double ideal_a = x + 0.5 - ww / 2.0;
            int cen_a = (int)round(ideal_a);
            cen_a = max(low_a, min(high_a, cen_a));
            double ideal_b = y + 0.5 - hh / 2.0;
            int cen_b = (int)round(ideal_b);
            cen_b = max(low_b, min(high_b, cen_b));
            // 5 tries
            vector<tuple<int, int, string>> tries = {
                {cen_a, cen_b, "center"},
                {low_a, cen_b, "left"},
                {high_a, cen_b, "right"},
                {cen_a, low_b, "bottom"},
                {cen_a, high_b, "top"}
            };
            for (auto& tr : tries) {
                int aa, bb;
                tie(aa, bb, ignore) = tr;
                int cc = aa + ww;
                int dd = bb + hh;
                if (check_valid(idx, aa, bb, cc, dd, X, Y, placed_rects)) {
                    A[idx] = aa;
                    B[idx] = bb;
                    C[idx] = cc;
                    D[idx] = dd;
                    placed_rects.push_back({aa, bb, cc, dd});
                    found = true;
                    break;
                }
            }
        }
        if (!found) {
            A[idx] = x;
            B[idx] = y;
            C[idx] = x + 1;
            D[idx] = y + 1;
            placed_rects.push_back({x, y, x + 1, y + 1});
        }
    }
    for (int i = 0; i < n; i++) {
        cout << A[i] << " " << B[i] << " " << C[i] << " " << D[i] << "\n";
    }
    return 0;
}