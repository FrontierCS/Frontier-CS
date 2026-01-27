#include <bits/stdc++.h>
using namespace std;

struct Edge {
    int u, c, v;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    if (n == 0) {
        cout << 0 << '\n';
        return 0;
    }

    int B = (n + 3) / 4;
    if (B < 1) B = 1;

    vector<Edge> edges;
    long long approx = (long long)(max(0, B - 1)) * (n + 1) + (long long)(n + 1);
    edges.reserve(approx);

    // Add edges of lengths 2..B: (i -> i+d) via intermediate i+1
    for (int d = 2; d <= B; ++d) {
        for (int i = 0; i + d <= n; ++i) {
            edges.push_back({i, i + 1, i + d});
        }
    }

    // Add edges of length 2B (if within bounds): (i -> i+2B) via intermediate i+B
    int L = 2 * B;
    if (L <= n) {
        for (int i = 0; i + L <= n; ++i) {
            edges.push_back({i, i + B, i + L});
        }
    }

    cout << edges.size() << '\n';
    for (const auto &e : edges) {
        cout << e.u << ' ' << e.c << ' ' << e.v << '\n';
    }

    return 0;
}