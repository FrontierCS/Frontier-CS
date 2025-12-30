#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    int m;
    if (!(cin >> n >> m)) return 0;

    vector<long long> posCnt(n + 1, 0), negCnt(n + 1, 0);

    for (int i = 0; i < m; ++i) {
        int a, b, c;
        cin >> a >> b >> c;
        int lits[3] = {a, b, c};
        for (int k = 0; k < 3; ++k) {
            int t = lits[k];
            if (t > 0) {
                if (t <= n) posCnt[t]++;
            } else {
                int v = -t;
                if (v <= n) negCnt[v]++;
            }
        }
    }

    for (int i = 1; i <= n; ++i) {
        int val = (posCnt[i] >= negCnt[i]) ? 1 : 0;
        if (i > 1) cout << ' ';
        cout << val;
    }
    cout << '\n';

    return 0;
}