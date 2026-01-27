#include <bits/stdc++.h>
using namespace std;

const long long MOD = 1000000007LL;

long long ask(const vector<long long>& a) {
    cout << "?";
    for (auto x : a) cout << " " << x;
    cout << endl;
    cout.flush();
    long long y;
    if (!(cin >> y)) exit(0);
    return y;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    if (n == 1) {
        vector<long long> a(2);
        a[0] = 3; a[1] = 2;
        long long r = ask(a);
        int op = (r == (3 + 2) % MOD) ? 0 : 1; // 0 for '+', 1 for '*'
        cout << "! " << op << endl;
        cout.flush();
        return 0;
    }

    vector<long long> r(n + 1, 0); // 1..n used
    for (int k = 1; k <= n; ++k) {
        vector<long long> a(n + 1, 1);
        a[0] = 2;
        a[k] = 2;
        r[k] = ask(a);
    }

    bool all_equal = true;
    for (int k = 2; k <= n; ++k) if (r[k] != r[1]) { all_equal = false; break; }

    vector<int> op(n + 1, 0); // 1..n, 0 for '+', 1 for '*'

    if (all_equal) {
        if (r[1] == 4 % MOD) {
            for (int i = 1; i <= n; ++i) op[i] = 1; // all '*'
        } else {
            for (int i = 1; i <= n; ++i) op[i] = 0; // all '+'
        }
    } else {
        vector<long long> D(n + 1, 0); // D[i] = signed diff r[i] - r[i-1], for i>=2
        for (int i = 2; i <= n; ++i) {
            long long dmod = r[i] - r[i - 1];
            if (dmod < 0) dmod += MOD;
            long long d = dmod;
            if (d > MOD / 2) d -= MOD;
            D[i] = d;
        }
        int i0 = 2;
        while (i0 <= n && D[i0] == 0) ++i0;
        // Determine op1
        if (D[i0] > 0) op[1] = 0; // '+'
        else op[1] = 1;          // '*'
        // Propagate
        for (int j = 2; j <= n; ++j) {
            if (D[j] == 0) op[j] = op[j - 1];
            else if (D[j] > 0) op[j] = 1; // '*'
            else op[j] = 0;               // '+'
        }
    }

    cout << "!";
    for (int i = 1; i <= n; ++i) cout << " " << op[i];
    cout << endl;
    cout.flush();

    return 0;
}