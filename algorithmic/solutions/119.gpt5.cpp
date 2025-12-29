#include <bits/stdc++.h>
using namespace std;

static const long long MOD = 1000000007LL;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    auto query = [&](const vector<long long>& a) -> long long {
        cout << "?";
        for (int i = 0; i <= n; ++i) cout << " " << a[i];
        cout << endl;
        cout.flush();
        long long y;
        if (!(cin >> y)) exit(0);
        if (y < 0) exit(0);
        return y % MOD;
    };

    vector<long long> res(n + 1, 0); // store responses for i=1..n

    // Perform n queries: a0=2, ai=2 for the specific i, all others 1
    for (int i = 1; i <= n; ++i) {
        vector<long long> a(n + 1, 1);
        a[0] = 2;
        a[i] = 2;
        res[i] = query(a);
    }

    vector<int> ans(n + 1, 1); // default all multiplication (1)
    bool allEqual = true;
    for (int i = 2; i <= n; ++i) {
        if (res[i] != res[1]) { allEqual = false; break; }
    }

    if (allEqual) {
        long long val = res[1];
        if (n == 1) {
            // Ambiguous when n=1 and val==4; resolve with one extra query
            vector<long long> a(n + 1, 1);
            a[0] = 2;
            a[1] = 3; // distinguish: 2+3=5 vs 2*3=6
            long long y = query(a);
            if (y == 5) ans[1] = 0; // plus
            else ans[1] = 1;        // multiply
        } else {
            if (val == 4) {
                // all multiplication; ans already 1
            } else {
                for (int i = 1; i <= n; ++i) ans[i] = 0; // all plus
            }
        }
    } else {
        long long minVal = res[1];
        for (int i = 2; i <= n; ++i) if (res[i] < minVal) minVal = res[i];
        for (int i = 1; i <= n; ++i) {
            if (res[i] == minVal) ans[i] = 0; // plus
            else ans[i] = 1;                  // multiply
        }
    }

    cout << "!";
    for (int i = 1; i <= n; ++i) cout << " " << ans[i];
    cout << endl;
    cout.flush();

    return 0;
}