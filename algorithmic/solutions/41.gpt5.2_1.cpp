#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    long long n;
    if (!(cin >> n)) return 0;

    vector<long long> a;
    long long x = 1;
    while (x <= n) {
        a.push_back(x);
        if (x > n / 2) break;
        x *= 2;
    }

    cout << a.size() << "\n";
    for (size_t i = 0; i < a.size(); i++) {
        if (i) cout << ' ';
        cout << a[i];
    }
    cout << "\n";
    return 0;
}