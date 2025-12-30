#include <bits/stdc++.h>
using namespace std;

static int read_int_or_exit() {
    int x;
    if (!(cin >> x)) exit(0);
    if (x == -1) exit(0);
    return x;
}

static int query_all_ones(int n) {
    cout << "? " << n;
    for (int i = 0; i < n; i++) cout << " 1";
    cout << '\n' << flush;
    return read_int_or_exit();
}

static int query_sep_1_to_k(int sep, int k) {
    int n = 2 * k;
    cout << "? " << n;
    for (int i = 1; i <= k; i++) {
        cout << ' ' << sep << ' ' << i;
    }
    cout << '\n' << flush;
    return read_int_or_exit();
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;
    for (int tc = 0; tc < t; tc++) {
        const int M = 100000;

        int L1 = query_all_ones(M);
        if (L1 == 1) {
            cout << "! " << M << '\n' << flush;
            continue;
        }

        long long lo = (M + (long long)L1 - 1) / L1;
        long long hi = (M - 1LL) / (L1 - 1LL);

        if (lo == hi) {
            cout << "! " << lo << '\n' << flush;
            continue;
        }

        int sep = (int)lo;
        int K = (int)(hi - lo);

        int L2 = query_sep_1_to_k(sep, K);
        long long W = sep + (2LL * K - L2);

        cout << "! " << W << '\n' << flush;
    }
    return 0;
}