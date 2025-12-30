#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, k;
    if (!(cin >> n >> k)) return 0;

    auto reset = [&]() {
        cout << "R\n";
        cout.flush();
    };

    auto ask = [&](int c) -> char {
        cout << "? " << c << "\n";
        cout.flush();
        char res;
        if (!(cin >> res)) exit(0);
        return res;
    };

    vector<int> parent(n + 1);
    iota(parent.begin(), parent.end(), 0);

    function<int(int)> findp = [&](int x) {
        return parent[x] == x ? x : parent[x] = findp(parent[x]);
    };

    auto unite = [&](int a, int b) {
        a = findp(a);
        b = findp(b);
        if (a != b) parent[b] = a;
    };

    // Brute-force all pairs: equality test via Reset, ?i, ?j
    for (int i = 1; i <= n; ++i) {
        for (int j = i + 1; j <= n; ++j) {
            reset();
            ask(i);            // ignore result
            char res = ask(j); // Y iff a_i == a_j
            if (res == 'Y') unite(i, j);
        }
    }

    int d = 0;
    for (int i = 1; i <= n; ++i) {
        if (findp(i) == i) ++d;
    }

    cout << "! " << d << "\n";
    cout.flush();
    return 0;
}