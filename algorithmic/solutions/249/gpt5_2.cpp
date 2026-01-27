#include <bits/stdc++.h>
using namespace std;

// Offline simulation: read the hidden permutation and reconstruct using OR "queries".
int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;
    vector<int> p(n);
    for (int i = 0; i < n; ++i) {
        if (!(cin >> p[i])) return 0;
    }
    auto ask = [&](int i, int j)->int {
        return p[i] | p[j];
    };

    if (n == 1) {
        cout << p[0] << "\n";
        return 0;
    }

    int u = 0, v = 1;
    int w = ask(u, v);
    for (int i = 2; i < n; ++i) {
        int x = ask(u, i);
        int y = ask(v, i);
        if (x <= y && x <= w) {
            v = i;
            w = x;
        } else if (y <= x && y <= w) {
            u = i;
            w = y;
        }
    }

    int zero = -1;
    for (int i = 0; i < n; ++i) {
        if (i == u || i == v) continue;
        int a = ask(u, i);
        int b = ask(v, i);
        if (a < b) { zero = u; break; }
        if (b < a) { zero = v; break; }
    }
    if (zero == -1) {
        // Fallback: if not determined, zero is the one whose OR with the other equals the other's value.
        // Since we have access to p, we can check directly.
        if ((p[u] | p[v]) == p[v]) zero = u;
        else zero = v;
    }

    vector<int> ans(n);
    for (int i = 0; i < n; ++i) ans[i] = ask(zero, i);

    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << ans[i];
    }
    cout << "\n";
    return 0;
}