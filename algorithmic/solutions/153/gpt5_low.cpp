#include <bits/stdc++.h>
using namespace std;

struct DSU {
    int n;
    vector<int> p, r;
    DSU(int n=0): n(n), p(n), r(n,0) { iota(p.begin(), p.end(), 0); }
    int find(int x){ return p[x]==x?x:p[x]=find(p[x]); }
    bool unite(int a,int b){
        a=find(a); b=find(b);
        if(a==b) return false;
        if(r[a]<r[b]) swap(a,b);
        p[b]=a;
        if(r[a]==r[b]) r[a]++;
        return true;
    }
    bool same(int a,int b){ return find(a)==find(b); }
};

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    const int N = 400;
    const int M = 1995;

    vector<int> x(N), y(N);
    for(int i=0;i<N;i++){
        if(!(cin>>x[i]>>y[i])) return 0;
    }
    vector<int> u(M), v(M), d(M);
    for(int i=0;i<M;i++){
        cin>>u[i]>>v[i];
        int dx = x[u[i]] - x[v[i]];
        int dy = y[u[i]] - y[v[i]];
        double dist = sqrt((double)dx*dx + (double)dy*dy);
        d[i] = (int)floor(dist + 0.5);
        if(d[i] <= 0) d[i] = 1; // safety
    }

    DSU dsu(N);
    int comp = N;

    for(int i=0;i<M;i++){
        long long li;
        if(!(cin>>li)) return 0;

        bool take = false;
        if(!dsu.same(u[i], v[i])){
            int need = comp - 1;
            int rem = M - i;
            double thr = 1.15 + 1.85 * (double)i / (double)max(1, M-1);

            // If we are running out of chances, relax aggressively
            if(rem <= need) thr = 3.0;
            else if(rem <= 2*need) thr = max(thr, 2.6);
            else if(rem <= 3*need) thr = max(thr, 2.3);
            else if(rem <= 5*need) thr = max(thr, 2.0);

            // Additional slight preference for very short absolute edges
            double ratio = (double)li / (double)max(1, d[i]);
            if(ratio <= thr) take = true;
        }

        if(take){
            cout << 1 << '\n' << flush;
            if(dsu.unite(u[i], v[i])) comp--;
        }else{
            cout << 0 << '\n' << flush;
        }
    }
    return 0;
}