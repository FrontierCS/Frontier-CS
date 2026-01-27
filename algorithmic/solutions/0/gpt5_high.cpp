#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;
    vector<long long> X(n), Y(n);
    vector<int> R(n, 0), F(n, 0);
    
    long long currS = 0;
    long long Hmax = 0;
    
    for (int i = 0; i < n; ++i) {
        int k;
        cin >> k;
        long long minx = LLONG_MAX, maxx = LLONG_MIN;
        long long miny = LLONG_MAX, maxy = LLONG_MIN;
        for (int j = 0; j < k; ++j) {
            long long x, y;
            cin >> x >> y;
            minx = min(minx, x);
            maxx = max(maxx, x);
            miny = min(miny, y);
            maxy = max(maxy, y);
        }
        long long width = maxx - minx + 1;
        long long height = maxy - miny + 1;
        
        X[i] = currS - minx;
        Y[i] = -miny;
        R[i] = 0;
        F[i] = 0;
        
        currS += width;
        Hmax = max(Hmax, height);
    }
    
    long long side = max(currS, Hmax); // make square to be safe if required
    long long W = side, H = side;
    
    cout << W << " " << H << "\n";
    for (int i = 0; i < n; ++i) {
        cout << X[i] << " " << Y[i] << " " << R[i] << " " << F[i] << "\n";
    }
    
    return 0;
}