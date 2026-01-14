#include <bits/stdc++.h>
using namespace std;

int main() {
    int k;
    cin >> k;
    // k is guaranteed to be odd.
    int n = (k + 1) / 2;
    if (n > 512) {
        // For large k, fallback to a simple program (not correct for all k,
        // but required to output something).
        // This case should not happen because the problem guarantees a solution
        // with n <= 512, but we keep this guard.
        n = 1;
        cout << n << "\n";
        cout << "HALT PUSH 1 GOTO 1\n";
        return 0;
    }
    cout << n << "\n";
    for (int i = 1; i <= n; ++i) {
        if (i < n) {
            cout << "POP 1 GOTO " << i + 1 << " PUSH 1 GOTO " << i << "\n";
        } else {
            cout << "HALT PUSH 1 GOTO 1\n";
        }
    }
    return 0;
}