#include <bits/stdc++.h>
using namespace std;

int main() {
    int h;
    cin >> h;
    int n = (1 << h) - 1;
    long long total = 0;
    long long mn = 1e18, mx = 0;
    for (int u = 1; u <= n; ++u) {
        cout << "? " << u << " 1" << endl;
        long long resp;
        cin >> resp;
        total += resp;
        mn = min(mn, resp);
        mx = max(mx, resp);
    }
    long long S;
    if (h == 2) {
        S = mn + mx;
    } else {
        S = total / 2;
    }
    cout << "! " << S << endl;
    return 0;
}