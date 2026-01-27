#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    if(!(cin >> n)) return 0;
    vector<int> a(n+1), pos(n+1);
    for(int i=1;i<=n;i++){ cin >> a[i]; pos[a[i]] = i; }

    int K = 2; // fixed segment length
    int t = K - 1;

    struct Op {int l, r, d;};
    vector<Op> ops;

    auto rotate_left = [&](int l){
        int r = l + K - 1;
        int tmp = a[l];
        for(int j=l;j<r;j++){
            a[j] = a[j+1];
            pos[a[j]] = j;
        }
        a[r] = tmp;
        pos[tmp] = r;
        ops.push_back({l, r, 0});
    };
    auto rotate_right = [&](int l){
        int r = l + K - 1;
        int tmp = a[r];
        for(int j=r;j>l;j--){
            a[j] = a[j-1];
            pos[a[j]] = j;
        }
        a[l] = tmp;
        pos[tmp] = l;
        ops.push_back({l, r, 1});
    };

    // Sorting by adjacent swaps (K=2); each rotation is just a swap.
    for(int i=1;i<=n;i++){
        int p = pos[i];
        while(p > i){
            // swap positions p-1 and p
            rotate_left(p-1);
            p--;
        }
    }

    cout << K << " " << ops.size() << "\n";
    for(auto &op: ops){
        cout << op.l << " " << op.r << " " << op.d << "\n";
    }
    return 0;
}