#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    if(!(cin >> n)) return 0;
    vector<int> a(n+1);
    for(int i=1;i<=n;i++) cin >> a[i];

    // Choose x = 3, allowed segment lengths are 2 and 4
    int x = 3;

    vector<pair<int,int>> ops;

    auto apply_rev = [&](int l, int r){
        reverse(a.begin()+l, a.begin()+r+1);
        ops.emplace_back(l, r);
    };

    // Greedy: place each element i at position i
    // Use length-4 reversals to move by 3 steps when possible, and length-2 (adjacent swap) otherwise
    vector<int> pos(n+1);
    for(int i=1;i<=n;i++) pos[a[i]] = i;

    for(int i=1;i<=n;i++){
        int p = pos[i];
        while(p > i){
            int gap = p - i;
            if(gap >= 3){
                // reverse [p-3, p] length 4, moves element at p to p-3
                int l = p - 3, r = p;
                apply_rev(l, r);
                // update positions
                // segment [l..r] reversed: positions map l<->r, l+1<->r-1
                // i moved from p to l
                // update pos of affected elements
                int v1 = a[l], v2 = a[l+1], v3 = a[l+2], v4 = a[l+3];
                // but after reverse already applied, a[l..r] is reversed
                // Recompute pos for affected values conservatively
                for(int k=l;k<=r;k++) pos[a[k]] = k;
                p = pos[i];
            }else if(gap == 2){
                // Use one adjacent swap (length 2) to reduce gap to 1
                int l = p - 1, r = p;
                apply_rev(l, r);
                for(int k=l;k<=r;k++) pos[a[k]] = k;
                p = pos[i];
            }else{ // gap == 1
                int l = p - 1, r = p;
                apply_rev(l, r);
                for(int k=l;k<=r;k++) pos[a[k]] = k;
                p = pos[i];
            }
        }
    }

    cout << x << "\n";
    cout << ops.size() << "\n";
    for(auto &op: ops){
        cout << op.first << " " << op.second << "\n";
    }
    return 0;
}