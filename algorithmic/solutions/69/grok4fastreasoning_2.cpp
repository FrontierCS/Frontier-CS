#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    cin >> n;
    for (int i = 1; i <= n; ++i) {
        string w(i, 'X');
        w += 'O';
        w += 'X';
        cout << w << '\n';
    }
    cout.flush();
    map<long long, pair<int, int>> power_to_pair;
    for (int i = 1; i <= n; ++i) {
        for (int j = 1; j <= n; ++j) {
            long long r1 = i;
            long long r2 = j + 1;
            long long mx = max(r1, r2);
            long long extra = max(0LL, r2 - r1);
            long long cross = r1 * r2 + extra;
            long long p = mx + 1 + mx + r2 + cross + 2 * r1 + 2;
            power_to_pair[p] = {i, j};
        }
    }
    int q;
    cin >> q;
    for (int qq = 0; qq < q; ++qq) {
        long long p;
        cin >> p;
        auto [ui, vi] = power_to_pair[p];
        cout << ui << ' ' << vi << '\n';
        cout.flush();
    }
    return 0;
}