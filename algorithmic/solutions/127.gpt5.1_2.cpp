#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) {
        cout << "! 0\n";
        cout.flush();
        return 0;
    }

    int ans = 0;
    bool found = false;

    for (int i = 0; i < n; ++i) {
        cout << "? " << i << "\n";
        cout.flush();

        int a0, a1;
        if (!(cin >> a0 >> a1)) {
            break; // Input failed; fall back to default answer
        }
        if (a0 == 0 && a1 == 0) {
            ans = i;
            found = true;
            break;
        }
    }

    if (!found) {
        ans = 0; // arbitrary index if not found
    }

    cout << "! " << ans << "\n";
    cout.flush();
    return 0;
}