#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;
    vector<int> x(n), y(n);
    vector<long long> r(n);
    for (int i = 0; i < n; ++i) {
        cin >> x[i] >> y[i] >> r[i];
    }

    for (int i = 0; i < n; ++i) {
        int a = x[i];
        int b = y[i];
        int c = x[i] + 1;
        int d = y[i] + 1;
        cout << a << ' ' << b << ' ' << c << ' ' << d << '\n';
    }

    return 0;
}