#include <bits/stdc++.h>
using namespace std;

struct Company {
    int x, y, r, a, b, c, d;
    long long area;
};

double compute_p(long long s, int rr) {
    if (s <= 0) return 0.0;
    double minv = min((double)s, (double)rr);
    double maxv = max((double)s, (double)rr);
    double rat = minv / maxv;
    return 1.0 - pow(1.0 - rat, 2.0);
}

int main() {
    int n;
    cin >> n;
    vector<Company> comp(n);
    for(int i = 0; i < n; i++) {
        cin >> comp[i].x >> comp[i].y >> comp[i].r;
        comp[i].a = comp[i].x;
        comp[i].b = comp[i].y;
        comp[i].c = comp[i].x + 1;
        comp[i].d = comp[i].y + 1;
        comp[i].area = 1LL;
    }
    vector<int> order(n);
    iota(order.begin(), order.end(), 0);
    sort(order.begin(), order.end(), [&](int i, int j) {
        return comp[i].r > comp[j].r || (comp[i].r == comp[j].r && i < j);
    });
    for(int oi = 0; oi < n; oi++) {
        int i = order[oi];
        int ai = comp[i].a, bi = comp[i].b, ci = comp[i].c, di = comp[i].d;
        int current_w = ci - ai;
        int current_h = di - bi;
        long long current_s = comp[i].area;
        int rr = comp[i].r;
        // maxl
        int max_cj_l = 0;
        for(int j = 0; j < n; j++) if(j != i) {
            int ajj = comp[j].a, bjj = comp[j].b, cjj = comp[j].c, djj = comp[j].d;
            if (max(bi, bjj) < min(di, djj)) {
                if (cjj < ai) {
                    max_cj_l = max(max_cj_l, cjj);
                }
            }
        }
        int maxl = ai - max_cj_l;
        // maxr
        int min_aj_r = 10001;
        for(int j = 0; j < n; j++) if(j != i) {
            int ajj = comp[j].a, bjj = comp[j].b, cjj = comp[j].c, djj = comp[j].d;
            if (max(bi, bjj) < min(di, djj)) {
                if (ajj > ci) {
                    min_aj_r = min(min_aj_r, ajj);
                }
            }
        }
        int maxrr = (min_aj_r == 10001 ? 10000 - ci : min_aj_r - ci);
        // maxdb
        int min_bj_d = 10001;
        for(int j = 0; j < n; j++) if(j != i) {
            int ajj = comp[j].a, cjj = comp[j].c, bjj = comp[j].b, djj = comp[j].d;
            if (max(ai, ajj) < min(ci, cjj)) {
                if (bjj > bi) {
                    min_bj_d = min(min_bj_d, bjj);
                }
            }
        }
        int maxdbb = (min_bj_d == 10001 ? bi : min_bj_d - bi);
        // maxdu
        int max_dj_u = 0;
        for(int j = 0; j < n; j++) if(j != i) {
            int ajj = comp[j].a, cjj = comp[j].c, bjj = comp[j].b, djj = comp[j].d;
            if (max(ai, ajj) < min(ci, cjj)) {
                if (djj < di) {
                    max_dj_u = max(max_dj_u, djj);
                }
            }
        }
        int maxduu = (max_dj_u == 0 ? 10000 - di : di - max_dj_u);
        int max_pos_w = current_w + maxl + maxrr;
        int max_pos_h = current_h + maxdbb + maxduu;
        // find best
        double best_p = compute_p(current_s, rr);
        int best_ww = current_w;
        int best_hh = current_h;
        int hminn = current_h;
        int hmaxx = max_pos_h;
        for(int ww = current_w; ww <= max_pos_w; ++ww) {
            double ttt = (double)rr / (double)ww;
            vector<int> cands;
            int hh_cand1 = -1;
            int hh_cand2 = -1;
            if (ttt <= hminn) {
                hh_cand1 = hminn;
            } else if (ttt >= hmaxx) {
                hh_cand1 = hmaxx;
            } else {
                double fl = floor(ttt);
                double ce = ceil(ttt);
                hh_cand1 = (int)fl;
                hh_cand2 = (int)ce;
            }
            if (hh_cand1 >= hminn && hh_cand1 <= hmaxx) cands.push_back(hh_cand1);
            if (hh_cand2 >= hminn && hh_cand2 <= hmaxx && hh_cand2 != hh_cand1) cands.push_back(hh_cand2);
            if (cands.empty()) {
                // fallback to hminn
                cands.push_back(hminn);
            }
            double max_p_ww = -1.0;
            int best_hh_ww = hminn;
            for(int hhc : cands) {
                long long ss = (long long)ww * hhc;
                double pp = compute_p(ss, rr);
                if (pp > max_p_ww) {
                    max_p_ww = pp;
                    best_hh_ww = hhc;
                }
            }
            if (max_p_ww > best_p) {
                best_p = max_p_ww;
                best_ww = ww;
                best_hh = best_hh_ww;
            }
        }
        // expand
        int extra_w = best_ww - current_w;
        int l = min(maxl, extra_w);
        int radd = extra_w - l;
        int extra_hh = best_hh - current_h;
        int db = min(maxdbb, extra_hh);
        int duu = extra_hh - db;
        comp[i].a = ai - l;
        comp[i].b = bi - db;
        comp[i].c = ci + radd;
        comp[i].d = di + duu;
        comp[i].area = (long long)(comp[i].c - comp[i].a) * (comp[i].d - comp[i].b);
    }
    for(int i = 0; i < n; i++) {
        cout << comp[i].a << " " << comp[i].b << " " << comp[i].c << " " << comp[i].d << "\n";
    }
    return 0;
}