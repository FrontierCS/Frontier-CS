#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    if (!(cin >> T)) return 0;

    int n, m;
    if (!(cin >> n >> m)) return 0;

    for (int tc = 0; tc < T; ++tc) {
        vector<pair<int,int>> edges(m);
        for (int i = 0; i < m; ++i) {
            int a, b;
            cin >> a >> b;
            edges[i] = {a, b};
        }

        cout << "! ";
        for (int i = 0; i < m; ++i) {
            cout << 1 << (i + 1 < m ? ' ' : '\n');
        }
        cout.flush();

        if (tc + 1 < T) {
            long long x;
            // Skip all response tokens (expected to be 0/1/-1), find next test's n (>=2)
            while (cin >> x) {
                if (x >= 2) {
                    n = (int)x;
                    break;
                }
            }
            if (!cin) return 0;
            if (!(cin >> m)) return 0;
        }
    }

    return 0;
}