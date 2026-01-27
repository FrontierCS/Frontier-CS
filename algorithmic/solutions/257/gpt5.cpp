#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    vector<long long> a(n);
    for (int i = 1; i <= n; ++i) {
        cout << "? " << i << " " << i << endl;
        cout.flush();
        long long x, f;
        if (!(cin >> x)) return 0;
        if (x == -1) return 0;
        if (!(cin >> f)) return 0;
        a[i - 1] = x;
    }

    cout << "!";
    for (int i = 0; i < n; ++i) {
        cout << " " << a[i];
    }
    cout << endl;
    cout.flush();

    return 0;
}