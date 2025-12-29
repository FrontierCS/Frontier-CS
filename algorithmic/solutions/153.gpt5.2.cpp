#include <bits/stdc++.h>
using namespace std;

struct DSU {
    int n;
    vector<int> p, sz;
    int comps;
    DSU(int n_=0){ init(n_); }
    void init(int n_){
        n=n_;
        p.resize(n);
        sz.assign(n,1);
        iota(p.begin(), p.end(), 0);
        comps=n;
    }
    int find(int a){
        while(p[a]!=a){
            p[a]=p[p[a]];
            a=p[a];
        }
        return a;
    }
    bool same(int a,int b){ return find(a)==find(b); }
    bool unite(int a,int b){
        a=find(a); b=find(b);
        if(a==b) return false;
        if(sz[a]<sz[b]) swap(a,b);
        p[b]=a;
        sz[a]+=sz[b];
        comps--;
        return true;
    }
};

static inline int rounded_dist(int x1,int y1,int x2,int y2){
    long long dx = (long long)x1 - x2;
    long long dy = (long long)y1 - y2;
    double dist = sqrt((double)dx*dx + (double)dy*dy);
    long long r = llround(dist);
    if(r < 0) r = 0;
    return (int)r;
}

int main(){
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
        d[i] = rounded_dist(x[u[i]], y[u[i]], x[v[i]], y[v[i]]);
        if(d[i] <= 0) d[i] = 1;
    }

    vector<int> ds = d;
    sort(ds.begin(), ds.end());
    int d30 = ds[(int)((long long)M * 3 / 10)];
    int d60 = ds[(int)((long long)M * 6 / 10)];

    vector<int> idx(M);
    iota(idx.begin(), idx.end(), 0);
    sort(idx.begin(), idx.end(), [&](int a, int b){
        if(d[a] != d[b]) return d[a] < d[b];
        if(u[a] != u[b]) return u[a] < u[b];
        return v[a] < v[b];
    });
    vector<char> inMST(M, 0);
    {
        DSU mst(N);
        for(int id: idx){
            if(mst.unite(u[id], v[id])) inMST[id] = 1;
            if(mst.comps == 1) break;
        }
    }

    DSU dsu(N);

    for(int i=0;i<M;i++){
        int li;
        if(!(cin >> li)) break;

        int ans = 0;

        if(dsu.comps == 1){
            ans = 0;
        }else if(dsu.same(u[i], v[i])){
            ans = 0;
        }else{
            bool mandatory = false;
            {
                DSU tmp = dsu;
                for(int j=i+1;j<M;j++) tmp.unite(u[j], v[j]);
                if(tmp.comps != 1) mandatory = true;
            }

            if(mandatory){
                ans = 1;
            }else{
                int cu = dsu.find(u[i]);
                int cv = dsu.find(v[i]);

                int k = 0;
                int mind = INT_MAX;
                for(int j=i;j<M;j++){
                    int a = dsu.find(u[j]);
                    int b = dsu.find(v[j]);
                    if((a==cu && b==cv) || (a==cv && b==cu)){
                        k++;
                        mind = min(mind, d[j]);
                    }
                }

                double edgesLeft = (double)(M - i);
                double mergesNeeded = (double)(dsu.comps - 1);
                double epm = edgesLeft / max(1.0, mergesNeeded);

                double t = 1.30 + 0.90 / sqrt(epm);
                double prog = (double)i / (double)(M - 1);
                t += 0.15 * prog;

                if(d[i] <= d30) t += 0.10;
                if(d[i] >= d60) t -= 0.05;
                if(inMST[i]) t += 0.10;
                if(k <= 2) t += 0.12;
                if(d[i] == mind) t += 0.06;

                t = min(2.40, max(1.12, t));

                double ratio = (double)li / (double)d[i];
                if(ratio <= t) ans = 1;
                else ans = 0;
            }
        }

        if(ans == 1) dsu.unite(u[i], v[i]);

        cout << ans << '\n' << flush;
    }

    return 0;
}