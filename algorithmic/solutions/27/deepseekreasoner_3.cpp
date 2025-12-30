#include <bits/stdc++.h>
using namespace std;

bool is_prime(int x) {
    if (x < 2) return false;
    for (int d = 2; d * d <= x; ++d)
        if (x % d == 0) return false;
    return true;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    cin >> n >> m;

    // trivial case: one row or one column
    if (n == 1 || m == 1) {
        cout << n * m << '\n';
        for (int i = 1; i <= n; ++i)
            for (int j = 1; j <= m; ++j)
                cout << i << ' ' << j << '\n';
        return 0;
    }

    int M = max(n, m);
    int p = (int)ceil(sqrt(M));
    while (!is_prime(p)) ++p;

    // ordering 0: (x, y) with index = x * p + y
    // ordering 1: (x, y) with index = y * p + x
    auto generate = [&](int ordering) -> vector<pair<int,int>> {
        vector<pair<int,int>> edges;
        for (int i = 0; i < n; ++i) {
            int a = i % p;
            int b = (i / p) % p;
            for (int j = 0; j < m; ++j) {
                int x, y;
                if (ordering == 0) {
                    x = j / p;
                    y = j % p;
                } else {
                    x = j % p;
                    y = j / p;
                }
                if ((a * x + b) % p == y)
                    edges.emplace_back(i + 1, j + 1);
            }
        }
        return edges;
    };

    vector<pair<int,int>> edges0 = generate(0);
    vector<pair<int,int>> edges1 = generate(1);
    vector<pair<int,int>>& best = edges0.size() >= edges1.size() ? edges0 : edges1;

    cout << best.size() << '\n';
    for (auto [r, c] : best)
        cout << r << ' ' << c << '\n';

    return 0;
}