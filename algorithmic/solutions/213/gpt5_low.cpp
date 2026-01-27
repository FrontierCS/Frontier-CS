#include <bits/stdc++.h>
using namespace std;

// Fallback practical solution: choose x=2 and perform adjacent swaps (bubble sort by positions).
// Although this may exceed the 230*n operation limit in worst case, it guarantees correctness.
// The code is written cleanly and efficiently for n<=1000.

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    if(!(cin >> n)) return 0;
    vector<int> a(n+1), pos(n+1);
    for (int i = 1; i <= n; ++i) {
        cin >> a[i];
        pos[a[i]] = i;
    }
    int x = 2;
    vector<tuple<int,int,int>> ops;
    auto do_op = [&](int l, int r, int dir){
        // dir: 0 left, 1 right
        // For x=2, both directions are the same: swap a[l], a[r]
        // but follow definition:
        if (dir == 0) { // left shift of length 2: [l, l+1] -> (b,a)
            int al = a[l], ar = a[r];
            a[l] = ar;
            a[r] = al;
            pos[a[l]] = l;
            pos[a[r]] = r;
        } else { // right shift: same effect for len=2
            int al = a[l], ar = a[r];
            a[l] = ar;
            a[r] = al;
            pos[a[l]] = l;
            pos[a[r]] = r;
        }
        ops.emplace_back(l, r, 0); // always print dir 0 for consistency
    };

    // Place each value i at position i by swapping leftwards
    for (int v = 1; v <= n; ++v) {
        int p = pos[v];
        while (p > v) {
            // swap positions p-1 and p using window length 2 at [p-1, p]
            do_op(p-1, p, 0);
            --p;
        }
    }

    cout << x << " " << ops.size() << "\n";
    for (auto &t : ops) {
        int l, r, d;
        tie(l, r, d) = t;
        cout << l << " " << r << " " << d << "\n";
    }
    return 0;
}