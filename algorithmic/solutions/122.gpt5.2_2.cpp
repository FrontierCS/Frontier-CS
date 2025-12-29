#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;

    const int N = 100000;

    string q1;
    q1.reserve(10 + 2 * N + 2);
    q1 += "? 100000";
    for (int i = 0; i < N; i++) q1 += " 1";
    q1 += '\n';

    for (int tc = 0; tc < t; tc++) {
        cout << q1 << flush;

        long long k;
        if (!(cin >> k)) return 0;
        if (k == -1) return 0;

        if (k == 1) {
            cout << "! " << N << '\n' << flush;
            continue;
        }

        long long S = (N + k - 1) / k;      // lower bound of W
        long long R = (N - 1) / (k - 1);    // upper bound of W

        if (S == R) {
            cout << "! " << S << '\n' << flush;
            continue;
        }

        long long M = R - S;
        long long n2 = 2 * M;

        cout << "? " << n2;
        for (long long i = 1; i <= M; i++) {
            cout << ' ' << S << ' ' << i;
        }
        cout << '\n' << flush;

        long long l2;
        if (!(cin >> l2)) return 0;
        if (l2 == -1) return 0;

        long long W = S + 2 * M - l2;
        cout << "! " << W << '\n' << flush;
    }

    return 0;
}