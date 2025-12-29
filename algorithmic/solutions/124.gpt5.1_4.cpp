#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    vector<int> p;
    p.reserve(n);
    for (int i = 0; i < n; ++i) {
        int x;
        if (!(cin >> x)) {
            // If the permutation isn't provided, default to 1..n
            p.clear();
            for (int j = 0; j < n; ++j) p.push_back(j + 1);
            break;
        }
        p.push_back(x);
    }

    if ((int)p.size() < n) {
        p.clear();
        for (int i = 0; i < n; ++i) p.push_back(i + 1);
    }

    // Ensure p1 <= n/2 if possible by flipping to complement
    if (p[0] > n / 2) {
        for (int i = 0; i < n; ++i) {
            p[i] = n + 1 - p[i];
        }
    }

    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << p[i];
    }
    cout << '\n';

    return 0;
}