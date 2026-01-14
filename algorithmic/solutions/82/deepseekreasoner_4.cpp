#include <bits/stdc++.h>
using namespace std;

int query(int i, int j) {
    cout << "? " << i << " " << j << endl;
    int res;
    cin >> res;
    return res;
}

int main() {
    int n;
    cin >> n;

    // candidate for zero
    int cand = 1;
    int probe = 2;
    if (n == 2) probe = 2; // n>=3

    // get initial value for candidate with probe
    int val_cand = query(cand, probe);

    for (int i = 2; i <= n; i++) {
        if (i == cand || i == probe) continue;
        int val_i = query(i, probe);
        if ((val_cand | val_i) != val_i) {
            // cand cannot be zero
            cand = i;
            // if new candidate equals probe, change probe
            if (cand == probe) {
                // choose a new probe different from cand
                probe = 1;
                if (probe == cand) probe = 3;
            }
            val_cand = query(cand, probe);
        }
    }

    // now cand should be zero (hopefully)
    vector<int> p(n+1, 0);
    for (int i = 1; i <= n; i++) {
        if (i == cand) continue;
        p[i] = query(cand, i);
    }

    // output
    cout << "!";
    for (int i = 1; i <= n; i++) {
        cout << " " << p[i];
    }
    cout << endl;

    return 0;
}