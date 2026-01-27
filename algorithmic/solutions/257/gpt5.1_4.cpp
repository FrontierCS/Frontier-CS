#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    vector<long long> a(n + 1);

    for (int i = 1; i <= n; ++i) {
        cout << "? " << i << " " << i << "\n";
        cout.flush();
        long long x, f;
        if (!(cin >> x >> f)) return 0;
        if (x == -1) return 0; // invalid query or judge error
        a[i] = x;
    }

    cout << "! ";
    for (int i = 1; i <= n; ++i) {
        cout << a[i] << (i == n ? '\n' : ' ');
    }
    cout.flush();

    return 0;
}