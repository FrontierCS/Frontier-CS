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
    auto apply = [&](int l, int r){
        // lengths will be 2 or 4 by construction
        ops.emplace_back(l, r);
        reverse(a.begin()+l, a.begin()+r+1);
        for(int j=l;j<=r;j++) pos[a[j]] = j;
    };
    
    for(int i=1;i<=n;i++){
        int p = pos[i];
        while(p - i >= 3){
            apply(p-3, p);
            p = pos[i];
        }
        int d = p - i;
        if(d == 2){
            apply(p-1, p);
            p = pos[i];
            apply(p-1, p);
        } else if(d == 1){
            apply(p-1, p);
        }
    }
    
    int x = 3; // allowed lengths: 2 and 4
    cout << x << "\n";
    cout << (int)ops.size() << "\n";
    for(auto &op : ops){
        cout << op.first << " " << op.second << "\n";
    }
    return 0;
}