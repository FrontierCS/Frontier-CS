#include <bits/stdc++.h>
using namespace std;

static inline long long read_reply() {
    long long x;
    if (!(cin >> x)) exit(0);
    if (x == -1) exit(0);
    return x;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;

    const int N = 100000;

    while (t--) {
        // Query 1: N ones
        cout << "? " << N;
        for (int i = 0; i < N; i++) cout << " 1";
        cout << '\n' << flush;

        long long r1 = read_reply();

        int W = -1;
        if (r1 == 1) {
            W = 100000;
        } else {
            int L = (N + (int)r1 - 1) / (int)r1;
            int R = (N - 1) / ((int)r1 - 1);
            R = min(R, 100000);

            if (L == R) {
                W = L;
            } else {
                int k = R - L; // >= 1
                // Query 2: blocks (L, i) for i=1..k, total n=2k
                cout << "? " << (2 * k);
                for (int i = 1; i <= k; i++) {
                    cout << ' ' << L << ' ' << i;
                }
                cout << '\n' << flush;

                long long r2 = read_reply();
                // r2 = k + count_notfit, count_notfit = k - (W-L)
                // => W = L + 2k - r2
                W = L + 2 * k - (int)r2;
            }
        }

        cout << "! " << W << '\n' << flush;
    }
    return 0;
}