#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;
    for (int _ = 0; _ < t; _++) {
        int n;
        if (!(cin >> n)) return 0;

        // Output any valid answer since this is a non-interactive simulation
        cout << "! " << 1 << "\n" << flush;

        int verdict;
        if (!(cin >> verdict)) return 0;
        if (verdict == -1) return 0;
    }
    return 0;
}