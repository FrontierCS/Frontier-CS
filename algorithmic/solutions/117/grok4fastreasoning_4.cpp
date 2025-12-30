#include <bits/stdc++.h>
using namespace std;
typedef long double ld;

int N;
int qcount = 0;

ld query(ld x, ld y) {
    qcount++;
    cout << fixed << setprecision(15) << "? " << x << " " << y << endl;
    fflush(stdout);
    ld f;
    cin >> f;
    return f;
}

ld compute_A(ld s) {
    ld abs_s = fabsl(s);
    ld t1 = 1e12L / (1.0L + abs_s);
    ld t2 = 0.9L * t1;
    ld x1 = t1;
    ld y1 = s * t1;
    ld f1 = query(x1, y1);
    ld x2 = t2;
    ld y2 = s * t2;
    ld f2 = query(x2, y2);
    ld dt = t1 - t2;
    ld A = (f1 - f2) / dt;
    return A;
}

ld compute_g(ld y) {
    return query(0.0L, y);
}

ld compute_w_comp(ld bb) {
    ld eps = 0.1L;
    ld dy = 0.05L;
    ld yl1 = bb - eps;
    ld yl2 = yl1 + dy;
    ld gl1 = compute_g(yl1);
    ld gl2 = compute_g(yl2);
    ld sl = (gl2 - gl1) / dy;
    ld yr1 = bb + eps;
    ld yr2 = yr1 + dy;
    ld gr1 = compute_g(yr1);
    ld gr2 = compute_g(yr2);
    ld sr = (gr2 - gr1) / dy;
    return (sr - sl) / 2.0L;
}

vector<ld> find_kinks_general(ld low, ld high, function<ld(ld)> comp, ld tol = 1e-9L, ld small = 0.5L) {
    vector<ld> res;
    function<void(ld, ld)> rec = [&](ld l, ld h) {
        if (h - l < small) {
            ld m = (l + h) / 2;
            ld al = comp(l);
            ld am = comp(m);
            ld ah = comp(h);
            ld frac = (m - l) / (h - l);
            ld interp = al + frac * (ah - al);
            if (am > interp + tol) {
                res.push_back(m);
            }
            return;
        }
        ld mid = (l + h) / 2;
        ld al = comp(l);
        ld am = comp(mid);
        ld ah = comp(h);
        ld frac = (mid - l) / (h - l);
        ld interp = al + frac * (ah - al);
        if (am <= interp + tol) {
            return;
        }
        rec(l, mid);
        rec(mid, h);
    };
    rec(low, high);
    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    cout << fixed << setprecision(15);
    cin >> N;
    auto approx_a_vec = find_kinks_general(-10001.0L, 10001.0L, compute_A);
    vector<int> a_list;
    for (auto m : approx_a_vec) {
        a_list.push_back((int)roundl(m));
    }
    // assume size N
    sort(a_list.begin(), a_list.end());
    vector<ld> ws(N);
    for (int i = 0; i < N; i++) {
        ld aa = a_list[i];
        ws[i] = 1.0L / sqrtl(aa * aa + 1.0L);
    }
    auto approx_b_vec = find_kinks_general(-10001.0L, 10001.0L, compute_g, 1e-9L, 0.5L);
    vector<int> b_list(N, 0);
    vector<bool> assigned(N, false);
    for (auto m : approx_b_vec) {
        ld bb = roundl(m);
        ld w_comp = compute_w_comp(bb);
        bool found = false;
        // k=1
        for (int j = 0; j < N && !found; j++) {
            if (!assigned[j] && fabsl(ws[j] - w_comp) < 1e-6L) {
                b_list[j] = (int)roundl(bb);
                assigned[j] = true;
                found = true;
            }
        }
        if (found) continue;
        // k=2
        for (int j1 = 0; j1 < N && !found; j1++) {
            if (assigned[j1]) continue;
            for (int j2 = j1 + 1; j2 < N && !found; j2++) {
                if (assigned[j2]) continue;
                ld sumw = ws[j1] + ws[j2];
                if (fabsl(sumw - w_comp) < 1e-6L) {
                    b_list[j1] = (int)roundl(bb);
                    b_list[j2] = (int)roundl(bb);
                    assigned[j1] = assigned[j2] = true;
                    found = true;
                }
            }
        }
        if (found) continue;
        // k=3
        for (int j1 = 0; j1 < N && !found; j1++) {
            if (assigned[j1]) continue;
            for (int j2 = j1 + 1; j2 < N && !found; j2++) {
                if (assigned[j2]) continue;
                for (int j3 = j2 + 1; j3 < N && !found; j3++) {
                    if (assigned[j3]) continue;
                    ld sumw = ws[j1] + ws[j2] + ws[j3];
                    if (fabsl(sumw - w_comp) < 1e-6L) {
                        b_list[j1] = (int)roundl(bb);
                        b_list[j2] = (int)roundl(bb);
                        b_list[j3] = (int)roundl(bb);
                        assigned[j1] = assigned[j2] = assigned[j3] = true;
                        found = true;
                    }
                }
            }
        }
        // add k=4 if needed, similar
    }
    // output
    cout << "!";
    for (int aa : a_list) cout << " " << aa;
    for (int bb : b_list) cout << " " << bb;
    cout << endl;
    return 0;
}