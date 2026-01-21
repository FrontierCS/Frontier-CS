#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;
    while (t--) {
        int n;
        cin >> n;

        // Trivial (incorrect) placeholder strategy:
        // Just immediately choose pens 0 and 1 with no queries.
        cout << 1 << " " << 0 << " " << 1 << endl;
        cout.flush();
    }

    return 0;
}