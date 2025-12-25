#include <bits/stdc++.h>
using namespace std;

int main() {
    int n;
    cin >> n;
    vector<int> X(n), Y(n), R(n);
    for (int i = 0; i < n; i++) {
        cin >> X[i] >> Y[i] >> R[i];
    }
    map<int, vector<int>> groups;
    for (int i = 0; i < n; i++) {
        groups[X[i]].push_back(i);
    }
    vector<int> used_x;
    for (auto& p : groups) {
        used_x.push_back(p.first);
    }
    int m = used_x.size();
    vector<int> left_extra(m, 0);
    vector<int> right_extra(m, 0);
    // leftmost gap
    if (used_x[0] > 0) {
        left_extra[0] = used_x[0] - 0;
    }
    // rightmost gap
    if (used_x.back() < 9999) {
        right_extra[m - 1] = 10000 - (used_x.back() + 1);
    }
    // internal gaps
    for (int j = 0; j < m - 1; j++) {
        int gap_len = used_x[j + 1] - used_x[j] - 1;
        if (gap_len > 0) {
            int left_max_r = 0;
            for (int ii : groups[used_x[j]]) {
                left_max_r = max(left_max_r, R[ii]);
            }
            int right_max_r = 0;
            for (int ii : groups[used_x[j + 1]]) {
                right_max_r = max(right_max_r, R[ii]);
            }
            if (left_max_r >= right_max_r) {
                right_extra[j] = gap_len;
            } else {
                left_extra[j + 1] = gap_len;
            }
        }
    }
    vector<int> A(n), B(n), C(n), D(n);
    for (int jj = 0; jj < m; jj++) {
        int xx = used_x[jj];
        auto& lst = groups[xx];
        int k = lst.size();
        if (k == 1) {
            int i = lst[0];
            int extra_l = left_extra[jj];
            int extra_r = right_extra[jj];
            int wi = 1 + extra_l + extra_r;
            int ai = xx - extra_l;
            int ci = xx + 1 + extra_r;
            // best h for wi, R[i]
            double rr = R[i];
            int hh = (int) round(rr / (double) wi);
            hh = max(1, min(10000, hh));
            double bestp = -1;
            int best_hh = 1;
            for (int dh = -1; dh <= 1; dh++) {
                int hhh = hh + dh;
                if (hhh >= 1 && hhh <= 10000) {
                    long long ss = (long long) wi * hhh;
                    double mn = min(rr, (double) ss);
                    double mx = max(rr, (double) ss);
                    double t = mn / mx;
                    double pp = 2 * t - t * t;
                    if (pp > bestp) {
                        bestp = pp;
                        best_hh = hhh;
                    }
                }
            }
            int hi = best_hh;
            int bi = max(0, Y[i] + 1 - hi);
            int di = bi + hi;
            A[i] = ai;
            B[i] = bi;
            C[i] = ci;
            D[i] = di;
        } else {
            // multiple, minimal
            for (int i : lst) {
                A[i] = xx;
                C[i] = xx + 1;
                B[i] = Y[i];
                D[i] = Y[i] + 1;
            }
        }
    }
    for (int i = 0; i < n; i++) {
        cout << A[i] << " " << B[i] << " " << C[i] << " " << D[i] << endl;
    }
    return 0;
}