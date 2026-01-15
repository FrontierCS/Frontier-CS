#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    for (int i = 0; i < n; ++i) {
        // Just output a fixed guess for the cycle length.
        cout << "! " << 3 << endl;
        cout.flush();

        int res;
        if (!(cin >> res)) return 0;
        if (res == -1) return 0;
    }

    return 0;
}