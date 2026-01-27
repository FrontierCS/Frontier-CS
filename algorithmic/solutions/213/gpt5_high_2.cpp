#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    if(!(cin >> n)) return 0;
    vector<int> a(n+1);
    for(int i=1;i<=n;i++) cin >> a[i];

    int x = (n>=2 ? 2 : 1);
    vector<array<int,3>> ops;

    if(n >= 2){
        // insertion sort using adjacent swaps (segment length 2, left shift)
        vector<int> pos(n+1);
        for(int i=1;i<=n;i++) pos[a[i]] = i;
        for(int val=1; val<=n; val++){
            int p = pos[val];
            while(p > val){
                // rotate left [p-1, p] length=2
                int l = p-1, r = p;
                // perform left shift: a[l] -> a[r], a[r] -> a[l]
                swap(a[l], a[r]);
                // update positions
                pos[a[l]] = l;
                pos[a[r]] = r;
                ops.push_back({l, r, 0});
                p--;
            }
        }
    }

    cout << x << " " << ops.size() << "\n";
    for(auto &op: ops){
        cout << op[0] << " " << op[1] << " " << op[2] << "\n";
    }
    return 0;
}