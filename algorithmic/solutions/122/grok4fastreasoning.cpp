#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    cout.tie(NULL);
    long long N = 100000LL;
    int t;
    cin >> t;
    for (int cas = 0; cas < t; cas++) {
        // First query: 100000 words of length 1
        cout << "? 100000";
        for (long long i = 0; i < N; i++) {
            cout << " 1";
        }
        cout << endl << flush;
        long long l1;
        cin >> l1;
        if (l1 == -1) return 0;
        long long W;
        if (l1 == 1) {
            W = N;
        } else {
            long long L = (N + l1 - 1LL) / l1;
            long long HH = (N - 1LL) / (l1 - 1LL);
            long long H = min(N, HH);
            if (L == H) {
                W = L;
            } else {
                long long mm = H - L;
                long long totaln = 2 * mm;
                cout << "? " << totaln;
                for (long long off = 1; off <= mm; off++) {
                    cout << " " << L << " " << off;
                }
                cout << endl << flush;
                long long l2;
                cin >> l2;
                if (l2 == -1) return 0;
                long long ff = l2 - mm;
                W = L + mm - ff;
            }
        }
        cout << "! " << W << endl << flush;
    }
    return 0;
}