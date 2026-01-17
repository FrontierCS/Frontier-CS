#include <bits/stdc++.h>
using namespace std;

int main() {
    int h;
    cin >> h;
    int n = (1 << h) - 1;
    if (h == 2) {
        long long a1, a2, a3;
        cout << "? 1 1" << endl; cin >> a1;
        cout << "? 2 1" << endl; cin >> a2;
        cout << "? 3 1" << endl; cin >> a3;
        long long total = a1 + a2 + a3 - min({a1, a2, a3});
        cout << "! " << total << endl;
    } else {
        vector<long long> a(n + 1);
        long long sumA = 0;
        for (int u = 1; u <= n; ++u) {
            cout << "? " << u << " " << 1 << endl;
            cin >> a[u];
            sumA += a[u];
        }
        long long total = sumA / 2;
        cout << "! " << total << endl;
    }
    return 0;
}