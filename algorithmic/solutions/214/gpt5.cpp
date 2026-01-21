#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    if(!(cin >> n)) return 0;
    vector<int> a(n+1);
    for (int i = 1; i <= n; ++i) cin >> a[i];
    vector<int> pos(n+1);
    for (int i = 1; i <= n; ++i) pos[a[i]] = i;

    vector<pair<int,int>> ops;
    ops.reserve(max(300*n, 1));

    auto do_swap2 = [&](int l){
        // reverse [l, l+1]
        ops.emplace_back(l, l+1);
        int x = a[l], y = a[l+1];
        swap(a[l], a[l+1]);
        pos[x] = l+1;
        pos[y] = l;
    };

    auto do_rev4 = [&](int l){
        // reverse [l, l+3]
        ops.emplace_back(l, l+3);
        // elements: a[l], a[l+1], a[l+2], a[l+3]
        int v0 = a[l], v1 = a[l+1], v2 = a[l+2], v3 = a[l+3];
        a[l] = v3; a[l+1] = v2; a[l+2] = v1; a[l+3] = v0;
        pos[v3] = l;
        pos[v2] = l+1;
        pos[v1] = l+2;
        pos[v0] = l+3;
    };

    for (int i = 1; i <= n; ++i) {
        int p = pos[i];
        while (p - i >= 3) {
            // apply 4-length reversal ending at p to move i left by 3
            do_rev4(p - 3);
            p -= 3;
        }
        // Now p - i in {0,1,2}
        if (p == i) continue;
        else if (p == i + 1) {
            do_swap2(i);
        } else if (p == i + 2) {
            // two adjacent swaps within [i..i+2]
            do_swap2(i+1);
            do_swap2(i);
        }
    }

    cout << 3 << "\n";
    cout << ops.size() << "\n";
    for (auto &op : ops) {
        cout << op.first << " " << op.second << "\n";
    }
    return 0;
}