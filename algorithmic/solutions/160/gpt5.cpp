#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    vector<int> f(100);
    for (int i = 0; i < 100; i++) {
        if (!(cin >> f[i])) return 0;
    }

    for (int t = 0; t < 100; t++) {
        int p;
        if (!(cin >> p)) return 0;

        if (t < 99) {
            char dir;
            if (f[t] == 1) dir = 'L';
            else if (f[t] == 2) dir = 'R';
            else dir = 'F';
            cout << dir << '\n' << flush;
        }
        // For t == 99 (100th candy), we skip output as allowed.
    }

    return 0;
}