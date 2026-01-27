#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;
    vector<long long> minx(n), miny(n), width(n), height(n);
    vector<int> k(n);
    for (int i = 0; i < n; ++i) {
        cin >> k[i];
        long long mnx = LLONG_MAX, mxx = LLONG_MIN, mny = LLONG_MAX, mxy = LLONG_MIN;
        for (int j = 0; j < k[i]; ++j) {
            long long x, y;
            cin >> x >> y;
            mnx = min(mnx, x);
            mxx = max(mxx, x);
            mny = min(mny, y);
            mxy = max(mxy, y);
        }
        minx[i] = mnx;
        miny[i] = mny;
        width[i] = mxx - mnx + 1;
        height[i] = mxy - mny + 1;
    }

    // Determine target width using sqrt of total bounding-box area
    long long areaBoxes = 0;
    long long maxW = 0;
    for (int i = 0; i < n; ++i) {
        areaBoxes += width[i] * height[i];
        if (width[i] > maxW) maxW = width[i];
    }
    long double sq = sqrt((long double)areaBoxes);
    long long targetW = (long long)ceil(sq);
    if (targetW < maxW) targetW = maxW;

    vector<long long> X(n), Y(n);
    vector<int> R(n, 0), F(n, 0);

    long long curX = 0, curY = 0, rowH = 0;
    long long usedW = 0;
    for (int i = 0; i < n; ++i) {
        if (curX > 0 && curX + width[i] > targetW) {
            curY += rowH;
            curX = 0;
            rowH = 0;
        }
        X[i] = curX - minx[i];
        Y[i] = curY - miny[i];
        curX += width[i];
        rowH = max(rowH, height[i]);
        usedW = max(usedW, curX);
    }
    long long usedH = curY + rowH;

    // Optionally enforce square (to satisfy potential W=H requirement in some statements)
    long long W = max(usedW, usedH);
    long long H = W;

    cout << W << " " << H << "\n";
    for (int i = 0; i < n; ++i) {
        cout << X[i] << " " << Y[i] << " " << R[i] << " " << F[i] << "\n";
    }
    return 0;
}