#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    if (!(cin >> T)) return 0;
    while (T--) {
        int n;
        if (!(cin >> n)) return 0;

        cout << "! ";
        for (int i = 2; i <= n; ++i) {
            cout << 1 << " " << i << " " << 1;
            if (i != n) cout << " ";
        }
        cout << "\n";
        cout.flush();
    }
    return 0;
}