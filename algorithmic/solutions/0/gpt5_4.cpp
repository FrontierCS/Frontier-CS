#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if(!(cin >> n)) return 0;
    vector<long long> X(n), Y(n);
    vector<int> R(n, 0), F(n, 0);
    long long W = 0, H = 0;
    long long currentX = 0;

    for (int i = 0; i < n; ++i) {
        int k;
        cin >> k;
        long long minx = LLONG_MAX, miny = LLONG_MAX;
        long long maxx = LLONG_MIN, maxy = LLONG_MIN;
        for (int j = 0; j < k; ++j) {
            long long x, y;
            cin >> x >> y;
            minx = min(minx, x);
            maxx = max(maxx, x);
            miny = min(miny, y);
            maxy = max(maxy, y);
        }
        long long w = maxx - minx + 1;
        long long h = maxy - miny + 1;

        X[i] = currentX - minx;
        Y[i] = -miny;
        currentX += w;
        H = max(H, h);
    }
    W = currentX;

    cout << W << " " << H << "\n";
    for (int i = 0; i < n; ++i) {
        cout << X[i] << " " << Y[i] << " " << R[i] << " " << F[i] << "\n";
    }
    return 0;
}