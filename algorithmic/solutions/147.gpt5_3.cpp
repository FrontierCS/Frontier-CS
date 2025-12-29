#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    if (!(cin >> n)) return 0;
    vector<int> x(n), y(n);
    long long r;
    for (int i = 0; i < n; ++i) {
        cin >> x[i] >> y[i] >> r;
    }
    for (int i = 0; i < n; ++i) {
        int a = x[i];
        int b = y[i];
        int c = min(10000, x[i] + 1);
        int d = min(10000, y[i] + 1);
        // Ensure positive area: since 0<=x[i],y[i]<=9999, c,d will be >= a+1,b+1 respectively
        cout << a << ' ' << b << ' ' << c << ' ' << d << '\n';
    }
    return 0;
}