#include <bits/stdc++.h>
using namespace std;

int ask(int i, int j) {
    cout << "? 1 1\n";
    cout << i << "\n";
    cout << j << "\n";
    cout.flush();
    int F;
    if (!(cin >> F)) {
        exit(0);
    }
    return F;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;
    while (t--) {
        int n;
        cin >> n;

        int base = -1;

        // Step 1: find any non-demagnetized magnet (base)
        for (int i = 1; i <= n && base == -1; ++i) {
            for (int j = i + 1; j <= n; ++j) {
                int F = ask(i, j);
                if (F != 0) {
                    base = i;
                    break;
                }
            }
        }

        if (base == -1) {
            // According to the problem guarantees, this should never happen.
            // Terminate to avoid undefined behavior in interactive environment.
            return 0;
        }

        // Step 2: classify all magnets using 'base'
        vector<int> zeros;
        for (int i = 1; i <= n; ++i) {
            if (i == base) continue;
            int F = ask(base, i);
            if (F == 0) zeros.push_back(i);
        }

        cout << "! " << zeros.size();
        for (int x : zeros) cout << ' ' << x;
        cout << "\n";
        cout.flush();
    }

    return 0;
}