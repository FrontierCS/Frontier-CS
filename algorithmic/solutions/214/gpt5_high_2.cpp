#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;
    vector<int> a(n + 1), pos(n + 1);
    for (int i = 1; i <= n; ++i) {
        cin >> a[i];
        pos[a[i]] = i;
    }
    
    int x = 3; // allowed lengths: 2 and 4
    vector<pair<int,int>> ops;
    
    auto apply = [&](int l, int r) {
        ops.emplace_back(l, r);
        int i = l, j = r;
        while (i < j) {
            int va = a[i], vb = a[j];
            swap(a[i], a[j]);
            pos[va] = j;
            pos[vb] = i;
            ++i; --j;
        }
    };
    
    for (int i = 1; i <= n; ++i) {
        int p = pos[i];
        while (p - i >= 3) {
            apply(p - 3, p); // length 4
            p = pos[i];
        }
        p = pos[i];
        if (p == i) continue;
        else if (p == i + 1) {
            apply(i, i + 1); // length 2
        } else if (p == i + 2) {
            apply(i + 1, i + 2); // length 2
            apply(i, i + 1);     // length 2
        }
    }
    
    cout << x << "\n";
    cout << (int)ops.size() << "\n";
    for (auto &op : ops) {
        cout << op.first << " " << op.second << "\n";
    }
    return 0;
}