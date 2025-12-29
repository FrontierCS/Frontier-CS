#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    long long n, k;
    if (!(cin >> n >> k)) return 0;

    const long long Q_LIMIT = 50000;
    long long queries_used = 0;

    auto query = [&](int x, int y) -> long long {
        cout << "QUERY " << x << " " << y << endl;
        cout.flush();
        long long v;
        if (!(cin >> v)) exit(0);
        ++queries_used;
        return v;
    };

    auto done = [&](long long ans) {
        cout << "DONE " << ans << endl;
        cout.flush();
    };

    if (n * n <= Q_LIMIT) {
        vector<long long> vals;
        vals.reserve(n * n);
        for (int i = 1; i <= n; ++i) {
            for (int j = 1; j <= n; ++j) {
                vals.push_back(query(i, j));
            }
        }
        nth_element(vals.begin(), vals.begin() + (k - 1), vals.end());
        long long ans = vals[k - 1];
        done(ans);
    } else {
        int m = (int)min<long long>(n, Q_LIMIT);
        vector<long long> diag;
        diag.reserve(m);
        for (int i = 1; i <= m; ++i) {
            if (queries_used >= Q_LIMIT) break;
            diag.push_back(query(i, i));
        }

        if (diag.empty()) {
            done(0);
        } else {
            long double total = (long double)n * (long double)n;
            long double pos = (k == 1 || total == 1) ? 0.0L
                              : (long double)(k - 1) / (total - 1.0L);
            int idx = (int)llround(pos * (diag.size() - 1));
            if (idx < 0) idx = 0;
            if (idx >= (int)diag.size()) idx = (int)diag.size() - 1;
            nth_element(diag.begin(), diag.begin() + idx, diag.end());
            long long ans = diag[idx];
            done(ans);
        }
    }

    return 0;
}