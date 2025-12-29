#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    vector<long long> X(n), Y(n);
    vector<int> R(n, 0), F(n, 0);

    long long cur_x = 0;
    long long max_h = 0;

    for (int i = 0; i < n; ++i) {
        int k;
        cin >> k;
        long long min_x = LLONG_MAX, max_x = LLONG_MIN;
        long long min_y = LLONG_MAX, max_y = LLONG_MIN;
        for (int j = 0; j < k; ++j) {
            long long x, y;
            cin >> x >> y;
            min_x = min(min_x, x);
            max_x = max(max_x, x);
            min_y = min(min_y, y);
            max_y = max(max_y, y);
        }
        long long width = max_x - min_x + 1;
        long long height = max_y - min_y + 1;

        X[i] = cur_x - min_x;
        Y[i] = -min_y;
        // R[i] = 0; F[i] = 0; // already initialized

        cur_x += width;
        if (height > max_h) max_h = height;
    }

    long long base_W = cur_x;
    long long base_H = max_h;
    long long S = max(base_W, base_H);
    if (S <= 0) S = 1;

    cout << S << ' ' << S << '\n';
    for (int i = 0; i < n; ++i) {
        cout << X[i] << ' ' << Y[i] << ' ' << R[i] << ' ' << F[i] << '\n';
    }

    return 0;
}