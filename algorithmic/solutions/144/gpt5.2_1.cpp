#include <bits/stdc++.h>
using namespace std;

static int n;

static pair<int,int> ask_exclude(int a, int b) {
    vector<int> idx;
    idx.reserve(n - 2);
    for (int i = 1; i <= n; i++) {
        if (i == a || i == b) continue;
        idx.push_back(i);
    }
    cout << "0 " << (int)idx.size();
    for (int x : idx) cout << ' ' << x;
    cout << '\n';
    cout.flush();

    int m1, m2;
    if (!(cin >> m1 >> m2)) exit(0);
    if (m1 == -1 || m2 == -1) exit(0);
    return {m1, m2};
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    cin >> n;
    int m = n / 2;

    int U = -1; // some index with value > m (either m+1 or >=m+2)
    bool sawLowerPair = false;
    int candUpper = -1;

    for (int j = 2; j <= n; j++) {
        auto [x, y] = ask_exclude(1, j);
        if (x == m + 1 && y == m + 2) {
            sawLowerPair = true; // (1,j) both <= m
        } else if (candUpper == -1) {
            candUpper = j; // if 1 is <=m, then j is >m; otherwise could be anything
        }
    }

    if (!sawLowerPair) {
        U = 1; // 1 must be > m
    } else {
        U = candUpper; // since 1 is <=m, this j is guaranteed >m
    }

    int idxA = -1, idxB = -1;

    // Find idxA (value m) using U
    for (int i = 1; i <= n; i++) {
        if (i == U) continue;
        auto [x, y] = ask_exclude(U, i);
        if (x == m - 1 && y == m + 1) { // removed {m, >=m+2} => i is m, U is >=m+2
            idxA = i;
            break;
        }
        if (x == m - 1 && y == m + 2) { // removed {m, m+1} => U is m+1, i is m
            idxA = i;
            idxB = U;
            break;
        }
    }

    if (idxA == -1) exit(0);

    if (idxB == -1) {
        // Find idxB (value m+1) using idxA
        for (int i = 1; i <= n; i++) {
            if (i == idxA) continue;
            auto [x, y] = ask_exclude(idxA, i);
            if (x == m - 1 && y == m + 2) {
                idxB = i;
                break;
            }
        }
    }

    if (idxB == -1) exit(0);

    cout << "1 " << idxA << ' ' << idxB << '\n';
    cout.flush();
    return 0;
}