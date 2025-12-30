#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    const long long MOD = 1000000007LL;

    int n;
    if (!(cin >> n)) return 0;

    auto ask = [&](const vector<long long>& a) -> long long {
        cout << "?";
        for (long long x : a) cout << ' ' << x;
        cout << '\n' << flush;

        long long res;
        if (!(cin >> res)) exit(0);
        if (res == -1) exit(0);
        return res;
    };

    vector<long long> base(n + 1, 1);
    base[0] = 2;

    long long r0 = ask(base);
    long long plus_total = r0 - 2; // guaranteed small and non-negative with our construction

    vector<int> ans(n + 1, 1); // 0 for '+', 1 for '*'
    long long plus_known = 0;

    for (int i = 1; i <= n - 1; i++) {
        vector<long long> q = base;
        q[i] = 2;
        long long ri = ask(q);
        long long diff = ri - r0; // no wrap with our construction
        if (diff == 1) {
            ans[i] = 0;
            plus_known++;
        } else {
            ans[i] = 1;
        }
    }

    long long remaining_plus = plus_total - plus_known;
    ans[n] = (remaining_plus == 1 ? 0 : 1);

    cout << "!";
    for (int i = 1; i <= n; i++) cout << ' ' << ans[i];
    cout << '\n' << flush;

    return 0;
}