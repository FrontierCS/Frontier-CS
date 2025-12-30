#include <bits/stdc++.h>
using namespace std;

struct DSU {
    int n;
    vector<int> p, sz;
    int comp;
    DSU(int n=0){ init(n); }
    void init(int n_) {
        n = n_;
        p.resize(n);
        sz.assign(n, 1);
        iota(p.begin(), p.end(), 0);
        comp = n;
    }
    int find(int a){ return p[a]==a ? a : p[a]=find(p[a]); }
    bool unite(int a, int b){
        a = find(a); b = find(b);
        if(a==b) return false;
        if(sz[a] < sz[b]) swap(a,b);
        p[b]=a; sz[a]+=sz[b];
        comp--;
        return true;
    }
    bool same(int a, int b){ return find(a)==find(b); }
};

static inline int dist_round_int(int x1, int y1, int x2, int y2){
    long long dx = (long long)x1 - x2;
    long long dy = (long long)y1 - y2;
    long double sq = (long double)dx*dx + (long double)dy*dy;
    long double rt = sqrt(sq);
    return (int) llround(rt);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    const int N = 400;
    const int M = 1995;

    vector<int> x(N), y(N);
    for(int i=0;i<N;i++){
        if(!(cin >> x[i] >> y[i])) return 0;
    }

    vector<int> u(M), v(M), d(M);
    for(int i=0;i<M;i++){
        cin >> u[i] >> v[i];
        d[i] = dist_round_int(x[u[i]], y[u[i]], x[v[i]], y[v[i]]);
        if(d[i] <= 0) d[i] = 1;
    }

    vector<int> st(M, 0); // 0=unprocessed, 1=accepted, -1=rejected
    DSU acc(N);

    auto canReject = [&](int idx)->bool{
        DSU tmp(N);
        for(int j=0;j<M;j++){
            if(j==idx) continue;
            if(st[j]==-1) continue;
            tmp.unite(u[j], v[j]);
            if(tmp.comp==1) break;
        }
        return tmp.comp==1;
    };

    for(int i=0;i<M;i++){
        int l;
        cin >> l;

        int ans = 0;

        if(acc.comp == 1){
            ans = 0;
            st[i] = -1;
        } else if(acc.same(u[i], v[i])) {
            ans = 0;
            st[i] = -1;
        } else {
            int mergesNeeded = acc.comp - 1;
            int remainingEdges = M - i - 1;
            double s = (double)mergesNeeded / (double)max(1, remainingEdges);
            double p = (double)i / (double)M;
            double thr = 1.10 + 1.55 * s + 0.25 * p;
            thr = max(1.15, min(2.95, thr));

            double r = (double)l / (double)d[i];

            if(r <= thr){
                ans = 1;
                st[i] = 1;
                acc.unite(u[i], v[i]);
            } else {
                if(canReject(i)){
                    ans = 0;
                    st[i] = -1;
                } else {
                    ans = 1;
                    st[i] = 1;
                    acc.unite(u[i], v[i]);
                }
            }
        }

        cout << ans << '\n' << flush;
    }
    return 0;
}