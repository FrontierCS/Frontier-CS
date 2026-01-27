#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;
    struct PieceInfo {
        long long minx, miny, maxx, maxy;
    };
    vector<PieceInfo> pieces(n);
    long long maxDim = 1;
    for (int i = 0; i < n; ++i) {
        int k;
        cin >> k;
        long long minx = LLONG_MAX, miny = LLONG_MAX, maxx = LLONG_MIN, maxy = LLONG_MIN;
        for (int j = 0; j < k; ++j) {
            long long x, y;
            cin >> x >> y;
            minx = min(minx, x);
            miny = min(miny, y);
            maxx = max(maxx, x);
            maxy = max(maxy, y);
        }
        pieces[i] = {minx, miny, maxx, maxy};
        long long width = maxx - minx + 1;
        long long height = maxy - miny + 1;
        maxDim = max(maxDim, max(width, height));
    }
    
    long long B = 1;
    while (B * B < (long long)n) ++B;
    long long S = max(1LL, maxDim);
    long long W = S * B;
    long long H = W; // ensure square
    
    cout << W << " " << H << "\n";
    for (int i = 0; i < n; ++i) {
        long long bx = i % B;
        long long by = i / B;
        long long X = bx * S - pieces[i].minx;
        long long Y = by * S - pieces[i].miny;
        int R = 0;
        int F = 0;
        cout << X << " " << Y << " " << R << " " << F << "\n";
    }
    return 0;
}