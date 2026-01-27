#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) {
        cout << "! 0" << endl;
        return 0;
    }

    for (int i = 0; i < n; ++i) {
        cout << "? " << i << endl;
        cout.flush();

        int a0, a1;
        if (!(cin >> a0 >> a1)) {
            // If interaction fails, output arbitrary index and exit
            cout << "! 0" << endl;
            cout.flush();
            return 0;
        }

        if (a0 == 0 && a1 == 0) {
            cout << "! " << i << endl;
            cout.flush();
            return 0;
        }
    }

    // Fallback: if not found (shouldn't happen if interaction is correct)
    cout << "! 0" << endl;
    cout.flush();
    return 0;
}