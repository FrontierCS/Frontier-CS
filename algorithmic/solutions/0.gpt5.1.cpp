#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    vector<long long> minX(n), maxX(n), minY(n), maxY(n);
    vector<long long> width(n), heightVec(n);

    long long maxWidth = 0;

    for (int i = 0; i < n; ++i) {
        int k;
        cin >> k;
        long long x, y;
        cin >> x >> y;
        minX[i] = maxX[i] = x;
        minY[i] = maxY[i] = y;
        for (int j = 1; j < k; ++j) {
            cin >> x >> y;
            if (x < minX[i]) minX[i] = x;
            if (x > maxX[i]) maxX[i] = x;
            if (y < minY[i]) minY[i] = y;
            if (y > maxY[i]) maxY[i] = y;
        }
        width[i] = maxX[i] - minX[i] + 1;
        heightVec[i] = maxY[i] - minY[i] + 1;
        if (width[i] > maxWidth) maxWidth = width[i];
    }

    vector<long long> Tx(n), Ty(n);
    long long cumY = 0;
    for (int i = 0; i < n; ++i) {
        Tx[i] = -minX[i];
        Ty[i] = cumY - minY[i];
        cumY += heightVec[i];
    }

    long long H_total = cumY;
    long long W0 = maxWidth;
    long long L = max(W0, H_total);
    if (L <= 0) L = 1;

    cout << L << " " << L << "\n";
    for (int i = 0; i < n; ++i) {
        cout << Tx[i] << " " << Ty[i] << " 0 0\n";
    }

    return 0;
}