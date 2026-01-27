#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    if (!(cin >> T)) return 0;
    while (T--) {
        long long n;
        if (!(cin >> n)) return 0;

        // Trivial non-interactive placeholder: always guess 1 3.
        cout << "! " << 1 << " " << (n >= 3 ? 3 : 2) << endl;
        cout.flush();

        int r;
        if (!(cin >> r)) return 0;
        if (r == -1) return 0;
    }
    return 0;
}