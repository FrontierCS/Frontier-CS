#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    int r = 1;

    vector<vector<char>> anc(n + 1, vector<char>(n + 1, 0));
    for (int a = 1; a <= n; ++a) anc[a][r] = (a == r);

    auto ask = [&](int v, int s1, int s2) -> int {
        cout << "? 2 " << v << " " << s1 << " " << s2 << endl;
        cout.flush();
        int res;
        if (!(cin >> res)) exit(0);
        if (res == -1) exit(0);
        return res;
    };

    for (int b = 1; b <= n; ++b) if (b != r) {
        for (int a = 1; a <= n; ++a) {
            if (a == b || a == r) {
                anc[a][b] = 1;
                continue;
            }
            anc[a][b] = (char)ask(a, b, r);
        }
    }

    vector<pair<int,int>> edges;
    edges.reserve(n - 1);
    for (int b = 1; b <= n; ++b) if (b != r) {
        vector<int> A;
        A.reserve(n);
        for (int a = 1; a <= n; ++a) {
            if (a != b && anc[a][b]) A.push_back(a);
        }
        int p = -1;
        for (int a : A) {
            bool good = true;
            for (int a2 : A) {
                if (a == a2) continue;
                if (anc[a][a2]) { good = false; break; }
            }
            if (good) { p = a; break; }
        }
        if (p == -1) p = r;
        edges.emplace_back(p, b);
    }

    cout << "!" << endl;
    for (auto &e : edges) {
        cout << e.first << " " << e.second << endl;
    }
    cout.flush();

    return 0;
}