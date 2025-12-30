#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;
    vector<int> x(n), y(n);
    vector<long long> r(n);
    for (int i = 0; i < n; i++) cin >> x[i] >> y[i] >> r[i];

    for (int i = 0; i < n; i++) {
        int a = x[i], b = y[i], c = x[i] + 1, d = y[i] + 1;
        cout << a << ' ' << b << ' ' << c << ' ' << d << "\n";
    }
    return 0;
}