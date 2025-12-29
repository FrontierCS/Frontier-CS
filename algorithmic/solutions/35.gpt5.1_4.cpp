#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;
    for (int tc = 0; tc < t; ++tc) {
        int n;
        if (!(cin >> n)) return 0;
        if (n == -1) return 0; // judge says previous answer was wrong
        int N = 2 * n - 1;

        int singleton = -1;

        // Check numbers from 1 to n-1
        for (int x = 1; x < n && singleton == -1; ++x) {
            int L = 1, R = N;

            // Binary search to find one position where a[pos] = x
            while (L < R) {
                int mid = (L + R) / 2;
                int len = mid - L + 1;

                cout << "? " << x << " " << len;
                for (int i = L; i <= mid; ++i) {
                    cout << " " << i;
                }
                cout << "\n";
                cout.flush();

                int ans;
                if (!(cin >> ans)) return 0;
                if (ans == -1) return 0;

                if (ans == 1) {
                    R = mid;
                } else {
                    L = mid + 1;
                }
            }

            int pos = L; // found index with value x

            // Query all positions except pos to see if there's another occurrence
            int len = N - 1;
            cout << "? " << x << " " << len;
            for (int i = 1; i <= N; ++i) {
                if (i != pos) cout << " " << i;
            }
            cout << "\n";
            cout.flush();

            int ans;
            if (!(cin >> ans)) return 0;
            if (ans == -1) return 0;

            if (ans == 0) {
                singleton = x;
            }
        }

        // If none of 1..n-1 is singleton, then n is singleton
        if (singleton == -1) singleton = n;

        cout << "! " << singleton << "\n";
        cout.flush();
    }

    return 0;
}