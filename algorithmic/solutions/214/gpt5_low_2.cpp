#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    if(!(cin >> n)) return 0;
    vector<int> a(n+1);
    for(int i=1;i<=n;i++) cin >> a[i];

    // We'll choose x = 3, so allowed lengths are 2 and 4.
    int x = 3;
    vector<pair<int,int>> ops;

    auto apply_rev = [&](int l, int r){
        reverse(a.begin()+l, a.begin()+r+1);
        ops.emplace_back(l, r);
    };

    // For each i, move value i to position i using reversals of length 4 (prefer) and 2.
    for(int i=1;i<=n;i++){
        // find position of i
        int p = -1;
        for(int j=i;j<=n;j++){
            if(a[j]==i){ p = j; break; }
        }
        if(p==-1) continue;
        while(p > i){
            if(p - i >= 3 && p-3 >= 1){
                // use length 4 reversal [p-3, p] to move element at p to p-3
                apply_rev(p-3, p);
                p -= 3;
            }else{
                // use adjacent swap (length 2) [p-1, p]
                apply_rev(p-1, p);
                p -= 1;
            }
        }
    }

    cout << x << "\n";
    cout << ops.size() << "\n";
    for(auto &op : ops){
        cout << op.first << " " << op.second << "\n";
    }
    return 0;
}