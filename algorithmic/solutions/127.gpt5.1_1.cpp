#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) {
        // If no input, just output something and exit.
        cout << "! 0\n" << flush;
        return 0;
    }

    for (int i = 0; i < n; ++i) {
        cout << "? " << i << '\n' << flush;
        long long a0, a1;
        if (!(cin >> a0 >> a1)) {
            // Input ended unexpectedly; fall back to arbitrary answer.
            cout << "! 0\n" << flush;
            return 0;
        }
        if (a0 == 0 && a1 == 0) {
            cout << "! " << i << '\n' << flush;
            return 0;
        }
    }

    // Fallback (should not normally happen): output arbitrary index.
    cout << "! 0\n" << flush;
    return 0;
}