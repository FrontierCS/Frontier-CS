#include <bits/stdc++.h>
using namespace std;

struct DSU {
    int n;
    vector<int> p, sz;
    int comps;
    DSU(int n=0){ init(n); }
    void init(int n_) {
        n = n_;
        p.resize(n);
        sz.assign(n, 1);
        iota(p.begin(), p.end(), 0);
        comps = n;
    }
    int find(int a){
        while(p[a] != a){
            p[a] = p[p[a]];
            a = p[a];
        }
        return a;
    }
    bool unite(int a, int b){
        a = find(a); b = find(b);
        if(a == b) return false;
        if(sz[a] < sz[b]) swap(a,b);
        p[b] = a;
        sz[a] += sz[b];
        comps--;
        return true;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    const int N = 400;
    const int M = 1995;

    vector<int> x(N), y(N);
    for(int i=0;i<N;i++){
        if(!(cin >> x[i] >> y[i])) return 0;
    }
    vector<int> u(M), v(M);
    for(int i=0;i<M;i++){
        cin >> u[i] >> v[i];
    }

    vector<int> d(M);
    for(int i=0;i<M;i++){
        long long dx = x[u[i]] - x[v[i]];
        long long dy = y[u[i]] - y[v[i]];
        double dist = sqrt((double)dx*dx + (double)dy*dy);
        d[i] = (int)llround(dist);
        if(d[i] < 1) d[i] = 1;
    }

    DSU dsu(N);

    auto can_reject = [&](int idx)->bool{
        DSU tmp = dsu;
        for(int j=idx+1;j<M;j++){
            tmp.unite(u[j], v[j]);
        }
        return tmp.comps == 1;
    };

    for(int i=0;i<M;i++){
        int li;
        cin >> li;

        int ans = 0;
        if(dsu.comps == 1){
            ans = 0;
        } else {
            int ru = dsu.find(u[i]), rv = dsu.find(v[i]);
            if(ru == rv){
                ans = 0;
            } else {
                double p = (M <= 1) ? 1.0 : (double)i / (double)(M - 1);
                double q = 1.0 - (double)dsu.comps / (double)N;
                double thr = 1.6 + 0.7 * p + 0.6 * q;
                thr = min(2.8, max(1.5, thr));

                if((double)li <= thr * (double)d[i]){
                    ans = 1;
                    dsu.unite(ru, rv);
                } else {
                    if(can_reject(i)){
                        ans = 0;
                    } else {
                        ans = 1;
                        dsu.unite(ru, rv);
                    }
                }
            }
        }

        cout << ans << "\n" << flush;
    }

    return 0;
}