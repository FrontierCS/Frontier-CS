#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    const int S = 12; // block size per polyomino (>= 10 with margin)
    int B = (int)floor(sqrt((double)n));
    while (1LL * B * B < n) B++;
    int L = B * S;

    vector<long long> outX(n), outY(n);
    vector<int> outR(n, 0), outF(n, 0);

    for (int i = 0; i < n; i++) {
        int k;
        cin >> k;
        long long minx = (1LL << 60), miny = (1LL << 60);
        long long maxx = -(1LL << 60), maxy = -(1LL << 60);
        for (int j = 0; j < k; j++) {
            long long x, y;
            cin >> x >> y;
            minx = min(minx, x);
            miny = min(miny, y);
            maxx = max(maxx, x);
            maxy = max(maxy, y);
        }

        int col = i % B;
        int row = i / B;
        long long bx = 1LL * col * S;
        long long by = 1LL * row * S;

        outX[i] = bx - minx;
        outY[i] = by - miny;
    }

    cout << L << ' ' << L << "\n";
    for (int i = 0; i < n; i++) {
        cout << outX[i] << ' ' << outY[i] << ' ' << outR[i] << ' ' << outF[i] << "\n";
    }
    return 0;
}