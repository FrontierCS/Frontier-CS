#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    for (int i = 0; i < n; ++i) {
        cout << "? " << i << endl;
        int a0, a1;
        if (!(cin >> a0 >> a1)) {
            // In case of unexpected interaction failure, output something and exit.
            cout << "! " << 0 << endl;
            return 0;
        }
        if (a0 == 0 && a1 == 0) {
            cout << "! " << i << endl;
            return 0;
        }
    }

    // Fallback: should never happen under correct interaction.
    cout << "! " << 0 << endl;
    return 0;
}