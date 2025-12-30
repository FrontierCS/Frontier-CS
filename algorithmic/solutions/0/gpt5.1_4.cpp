#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    vector<long long> minX(n), maxX(n), minY(n), maxY(n);

    for (int i = 0; i < n; ++i) {
        int k;
        cin >> k;
        long long mnx = (1LL << 60), mxx = -(1LL << 60);
        long long mny = (1LL << 60), mxy = -(1LL << 60);
        for (int j = 0; j < k; ++j) {
            long long x, y;
            cin >> x >> y;
            mnx = min(mnx, x);
            mxx = max(mxx, x);
            mny = min(mny, y);
            mxy = max(mxy, y);
        }
        minX[i] = mnx;
        maxX[i] = mxx;
        minY[i] = mny;
        maxY[i] = mxy;
    }

    vector<long long> Xi(n), Yi(n);
    vector<int> Ri(n, 0), Fi(n, 0);

    long long maxHeight = 0;
    for (int i = 0; i < n; ++i) {
        long long height = maxY[i] - minY[i] + 1;
        if (height > maxHeight) maxHeight = height;
    }

    long long offsetX = 0;
    for (int i = 0; i < n; ++i) {
        long long width = maxX[i] - minX[i] + 1;
        Xi[i] = offsetX - minX[i];
        Yi[i] = -minY[i];
        offsetX += width + 1; // gap of 1 between pieces
    }

    long long W0 = offsetX;
    long long H0 = maxHeight;
    long long side = max(W0, H0);
    long long W = side, H = side; // ensure W = H as per statement

    cout << W << " " << H << '\n';
    for (int i = 0; i < n; ++i) {
        cout << Xi[i] << " " << Yi[i] << " " << Ri[i] << " " << Fi[i] << '\n';
    }

    return 0;
}