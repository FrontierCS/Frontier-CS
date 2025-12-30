#include <bits/stdc++.h>
using namespace std;

int main() {
    int N, L;
    cin >> N >> L;
    vector<int> T(N);
    for (int &x : T) cin >> x;
    vector<long long> req(N);
    for (int i = 0; i < N; i++) {
        req[i] = T[i];
        if (i == 0) req[i]--;
    }
    struct Bundle {
        long long size;
        int x;
        bool is_odd;
    };
    vector<Bundle> bundles;
    for (int x = 0; x < N; x++) {
        int c = (T[x] + 1) / 2;
        int f = T[x] / 2;
        if (c > 0) {
            bundles.push_back({c, x, true});
        }
        if (f > 0) {
            bundles.push_back({f, x, false});
        }
    }
    sort(bundles.begin(), bundles.end(), [](const Bundle& p, const Bundle& q) {
        return p.size > q.size;
    });
    vector<long long> current(N, 0);
    vector<int> A(N, 0), B(N, 0);
    for (auto &bd : bundles) {
        int best_y = -1;
        long long best_def = LLONG_MIN;
        for (int y = 0; y < N; y++) {
            long long def = req[y] - current[y];
            if (def > best_def || (def == best_def && y < best_y)) {
                best_def = def;
                best_y = y;
            }
        }
        current[best_y] += bd.size;
        if (bd.is_odd) {
            A[bd.x] = best_y;
        } else {
            B[bd.x] = best_y;
        }
    }
    for (int i = 0; i < N; i++) {
        cout << A[i] << " " << B[i] << "\n";
    }
}