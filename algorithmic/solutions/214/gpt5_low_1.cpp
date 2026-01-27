#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    if(!(cin >> n)) return 0;
    vector<int> a(n+1), pos(n+1);
    for(int i=1;i<=n;i++){
        cin >> a[i];
        pos[a[i]] = i;
    }
    vector<pair<int,int>> ops;

    auto do_rev = [&](int l, int r){
        // Only allow lengths 2 or 4
        int len = r-l+1;
        if(!(len==2 || len==4)) return;
        reverse(a.begin()+l, a.begin()+r+1);
        for(int i=l;i<=r;i++){
            pos[a[i]] = i;
        }
        ops.emplace_back(l, r);
    };

    // Choose x = 3 -> allowed lengths 2 and 4
    int x = 3;

    for(int target=1; target<=n; target++){
        int p = pos[target];
        while(p > target){
            if(p - target >= 3){
                // move left by 3 using length-4 reversal [p-3, p]
                do_rev(p-3, p);
                p -= 3;
            }else{
                // move left by 1 using length-2 reversal [p-1, p]
                do_rev(p-1, p);
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