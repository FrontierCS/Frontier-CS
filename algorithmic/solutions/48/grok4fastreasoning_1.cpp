#include <bits/stdc++.h>

using namespace std;

double get_pos(int size, int idx, double r) {
    if (size == 1) return 0.5;
    double d = (1.0 - 2 * r) / (size - 1.0);
    return r + idx * d;
}

int main() {
    int n;
    cin >> n;
    int best_l = INT_MAX;
    int bm = 0, bk = 0, bl = 0;
    for (int m = 1; m * m * m <= 2LL * n; ++m) {
        for (int k = m;; ++k) {
            if (1LL * m * k * k < n) continue;
            int l = (n + 1LL * m * k - 1) / (1LL * m * k);
            if (l < k) break;
            if (l > best_l) continue;
            if (1LL * m * k * l >= n) {
                best_l = l;
                bm = m;
                bk = k;
                bl = l;
            }
        }
    }
    int M = best_l;
    double r = 1.0 / (2 * M);
    vector<tuple<double, double, double>> centers;
    int placed = 0;
    for (int i = 0; i < bm && placed < n; ++i) {
        double x = get_pos(bm, i, r);
        for (int j = 0; j < bk && placed < n; ++j) {
            double y = get_pos(bk, j, r);
            for (int ii = 0; ii < bl && placed < n; ++ii) {
                double z = get_pos(bl, ii, r);
                centers.emplace_back(x, y, z);
                ++placed;
                if (placed == n) goto done;
            }
        }
    }
done:
    for (auto [x, y, z] : centers) {
        printf("%.10f %.10f %.10f\n", x, y, z);
    }
    return 0;
}