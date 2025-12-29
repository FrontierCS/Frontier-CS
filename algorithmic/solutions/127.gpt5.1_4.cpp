#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    for (int i = 0; i < n; ++i) {
        cout << "? " << i << '\n';
        cout.flush();

        int a0, a1;
        if (!(cin >> a0 >> a1)) {
            // Fallback for non-interactive environment: output arbitrary index.
            cout << "! " << 0 << '\n';
            cout.flush();
            return 0;
        }

        if (a0 == 0 && a1 == 0) {
            cout << "! " << i << '\n';
            cout.flush();
            return 0;
        }
    }

    // If not found (shouldn't happen with a correct judge), output arbitrary index.
    cout << "! " << 0 << '\n';
    cout.flush();
    return 0;
}