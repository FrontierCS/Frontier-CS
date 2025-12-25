#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    const long long INF = (1LL << 60);
    vector<long long> minx(n), maxx(n), miny(n), maxy(n);

    for (int i = 0; i < n; ++i) {
        int k;
        cin >> k;
        minx[i] = miny[i] = INF;
        maxx[i] = maxy[i] = -INF;
        for (int j = 0; j < k; ++j) {
            long long x, y;
            cin >> x >> y;
            if (x < minx[i]) minx[i] = x;
            if (x > maxx[i]) maxx[i] = x;
            if (y < miny[i]) miny[i] = y;
            if (y > maxy[i]) maxy[i] = y;
        }
    }

    vector<long long> X(n), Y(n);
    long long x_offset = 0;
    long long max_h = 0;

    for (int i = 0; i < n; ++i) {
        long long w = maxx[i] - minx[i] + 1;
        long long h = maxy[i] - miny[i] + 1;

        X[i] = x_offset - minx[i];
        Y[i] = -miny[i];

        x_offset += w;
        if (h > max_h) max_h = h;
    }

    long long W_strip = x_offset;
    long long H_strip = max_h;
    long long side = max(W_strip, H_strip);
    if (side <= 0) side = 1;

    long long W = side;
    long long H = side;

    cout << W << ' ' << H << '\n';
    for (int i = 0; i < n; ++i) {
        cout << X[i] << ' ' << Y[i] << ' ' << 0 << ' ' << 0 << '\n';
    }

    return 0;
}