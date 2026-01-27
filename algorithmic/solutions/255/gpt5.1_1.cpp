#include <bits/stdc++.h>
using namespace std;

long long ask(int i, int j) {
    cout << "? 1 1\n";
    cout << i << "\n";
    cout << j << "\n";
    cout.flush();
    long long F;
    if (!(cin >> F)) {
        exit(0);
    }
    return F;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    if (!(cin >> T)) return 0;
    while (T--) {
        int n;
        cin >> n;

        int base = -1, partner = -1;

        // Find a pair of non-zero magnets
        for (int i = 1; i <= n && base == -1; ++i) {
            for (int j = i + 1; j <= n; ++j) {
                long long F = ask(i, j);
                if (F != 0) {
                    base = i;
                    partner = j;
                    break;
                }
            }
        }

        vector<int> zeros;
        vector<int> nonzero(n + 1, 0);

        if (base == -1) {
            // Should not happen as per problem guarantees
            // Fallback: assume all are zero except first two (arbitrary),
            // but this situation shouldn't occur.
            for (int i = 1; i <= n; ++i) zeros.push_back(i);
        } else {
            nonzero[base] = 1;
            if (partner != -1) nonzero[partner] = 1;

            // Classify all magnets using base
            for (int i = 1; i <= n; ++i) {
                if (i == base || nonzero[i]) continue;
                long long F = ask(base, i);
                if (F == 0) {
                    zeros.push_back(i);
                } else {
                    nonzero[i] = 1;
                }
            }
        }

        cout << "! " << zeros.size();
        for (int x : zeros) cout << " " << x;
        cout << "\n";
        cout.flush();
    }

    return 0;
}