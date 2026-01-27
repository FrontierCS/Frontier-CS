#include <bits/stdc++.h>
using namespace std;

long long ask(int u, int v) {
    cout << "? " << u << " " << v << "\n";
    cout.flush();
    long long d;
    if (!(cin >> d)) exit(0);
    return d;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    vector<long long> d1(n+1, 0), da(n+1, 0), db(n+1, 0);

    // Get distances from node 1
    d1[1] = 0;
    int a = 1;
    long long maxd = -1;
    for (int i = 2; i <= n; ++i) {
        d1[i] = ask(1, i);
        if (d1[i] > maxd) {
            maxd = d1[i];
            a = i;
        }
    }

    // Get distances from node a
    long long L = 0;
    int b = a;
    for (int i = 1; i <= n; ++i) {
        if (i == a) {
            da[i] = 0;
        } else {
            da[i] = ask(a, i);
        }
        if (da[i] > L) {
            L = da[i];
            b = i;
        }
    }

    // Get distances from node b (optional to locate the center precisely)
    for (int i = 1; i <= n; ++i) {
        if (i == b) db[i] = 0;
        else db[i] = ask(b, i);
    }

    // The center of the diameter path is a node c such that da[c] + db[c] = L
    // and da[c] is floor(L/2) (unique when L even, one of two when L odd).
    long long targetA = L / 2; // floor
    int center = 1;
    for (int i = 1; i <= n; ++i) {
        if (da[i] + db[i] == L && da[i] == targetA) {
            center = i;
            break;
        }
    }

    cout << "! " << center << "\n";
    cout.flush();
    return 0;
}