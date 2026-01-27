#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int h;
    if(!(cin >> h)) return 0;
    int n = (1 << h) - 1;
    int D = 2 * (h - 1);

    vector<int> odd;
    for (int d = 1; d <= D; d += 2) odd.push_back(d);

    long long val1 = LLONG_MIN, val2 = LLONG_MIN;

    for (int u = 1; u <= n; ++u) {
        long long s = 0;
        for (int d : odd) {
            cout << "? " << u << " " << d << endl;
            cout.flush();
            long long x;
            if (!(cin >> x)) return 0;
            s += x;
        }
        if (val1 == LLONG_MIN) val1 = s;
        else if (s != val1) { val2 = s; break; }
    }

    long long ans;
    if (val2 == LLONG_MIN) ans = 2 * val1;
    else ans = val1 + val2;

    cout << "! " << ans << endl;
    cout.flush();
    return 0;
}