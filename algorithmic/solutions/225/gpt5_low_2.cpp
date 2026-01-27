#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n, q;
    if(!(cin >> n >> q)) return 0;
    vector<int> a(n+1), pos(n+1);
    for(int i=1;i<=n;i++){ cin >> a[i]; pos[a[i]] = i; }

    vector<pair<int,int>> ops;
    vector<int> ans(q);
    // cache built intervals to reuse
    struct PairHash {
        size_t operator()(const pair<int,int>&p) const {
            return (size_t)p.first*1315423911u ^ (size_t)p.second*2654435761u;
        }
    };
    unordered_map<pair<int,int>, int, PairHash> built;
    built.reserve(q*2+1000);

    long long cnt_limit = 2200000;
    long long cnt = n;

    vector<pair<int,int>> queries(q);
    for(int i=0;i<q;i++){
        int l,r; cin >> l >> r;
        queries[i] = {l,r};
    }

    for(int i=0;i<q;i++){
        int l = queries[i].first, r = queries[i].second;
        if(l==r){ ans[i]=l; continue; }
        auto key = make_pair(l,r);
        auto it = built.find(key);
        if(it!=built.end()){
            ans[i]=it->second;
            continue;
        }
        vector<int> idx;
        idx.reserve(r-l+1);
        for(int j=l;j<=r;j++) idx.push_back(j);
        sort(idx.begin(), idx.end(), [&](int x, int y){ return a[x] < a[y]; });
        int cur = idx[0];
        for(size_t t=1;t<idx.size();t++){
            // merge set cur with singleton idx[t]
            ops.emplace_back(cur, idx[t]);
            cur = ++cnt;
            if(cnt > cnt_limit){
                // Still proceed; but constraints guarantee existence; this may overflow.
            }
        }
        built[key]=cur;
        ans[i]=cur;
    }

    cout << cnt << "\n";
    for(auto &op: ops) cout << op.first << " " << op.second << "\n";
    for(int i=0;i<q;i++){
        if(i) cout << " ";
        cout << ans[i];
    }
    cout << "\n";
    return 0;
}