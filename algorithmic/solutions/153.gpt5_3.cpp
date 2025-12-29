#include <bits/stdc++.h>
using namespace std;

struct DSU {
    int n, comp;
    vector<int> p, r;
    DSU() {}
    DSU(int n): n(n), comp(n), p(n), r(n,0) { iota(p.begin(), p.end(), 0); }
    int find(int x){ return p[x]==x?x:p[x]=find(p[x]); }
    bool unite(int a, int b){
        a=find(a); b=find(b);
        if(a==b) return false;
        if(r[a]<r[b]) swap(a,b);
        p[b]=a;
        if(r[a]==r[b]) r[a]++;
        comp--;
        return true;
    }
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
    vector<int> u(M), v(M);
    for(int i=0;i<M;i++){
        if(!(cin>>u[i]>>v[i])) return 0;
    }

    // Precompute d_i
    vector<int> d(M);
    for(int i=0;i<M;i++){
        long long dx = x[u[i]] - x[v[i]];
        long long dy = y[u[i]] - y[v[i]];
        double dist = sqrt((double)dx*dx + (double)dy*dy);
        d[i] = (int)floor(dist + 0.5);
        if(d[i] <= 0) d[i] = 1; // just in case
    }

    // Build an MST on given edges with weight d as a hint
    vector<int> idx(M);
    iota(idx.begin(), idx.end(), 0);
    sort(idx.begin(), idx.end(), [&](int a, int b){
        if(d[a] != d[b]) return d[a] < d[b];
        if(u[a] != u[b]) return u[a] < u[b];
        return v[a] < v[b];
    });
    vector<char> in_mstd(M, 0);
    {
        DSU tdsu(N);
        int picked = 0;
        for(int id : idx){
            if(tdsu.unite(u[id], v[id])){
                in_mstd[id] = 1;
                picked++;
                if(picked == N-1) break;
            }
        }
    }

    DSU accepted(N);

    // Parameters
    const double THR_LO = 1.25;
    const double THR_HI = 2.30;
    const double THR_MSTD = 2.00;
    const double RMAX = 7.0;

    for(int i=0;i<M;i++){
        int li;
        if(!(cin>>li)) return 0;

        int ru = accepted.find(u[i]);
        int rv = accepted.find(v[i]);

        if(ru == rv){
            cout << 0 << '\n' << flush;
            continue;
        }

        bool forced = false;
        {
            DSU tmp = accepted;
            for(int j=i+1;j<M;j++){
                tmp.unite(u[j], v[j]);
                if(tmp.comp == 1) break;
            }
            if(tmp.comp > 1) forced = true;
        }

        bool take = false;

        if(forced){
            take = true;
        }else{
            // compute Rcount and comps
            int comps = accepted.comp;
            long long Rcount = 0;
            for(int j=i;j<M;j++){
                if(accepted.find(u[j]) != accepted.find(v[j])) Rcount++;
            }
            double ratio = (double)Rcount / max(1, comps - 1);
            double rr = min(max(1.0, ratio), RMAX);
            double t = (rr - 1.0) / (RMAX - 1.0); // 0..1
            double thr_general = THR_HI - t * (THR_HI - THR_LO);

            double thr = thr_general;
            if(in_mstd[i]) thr = max(thr, THR_MSTD);

            // Slight endgame pressure: when few edges remain vs needed, push threshold up
            int remEdges = M - i;
            int need = comps - 1;
            if(need > 0){
                double tight = (double)remEdges / need; // smaller -> tighter
                if(tight < 3.0){
                    double add = (3.0 - tight) / 3.0; // 0..1
                    thr = min(3.0, thr + add * 0.5);
                }
            }

            if(li <= (int)floor(thr * d[i] + 1e-9)) take = true;
        }

        if(take){
            accepted.unite(u[i], v[i]);
            cout << 1 << '\n' << flush;
        }else{
            cout << 0 << '\n' << flush;
        }
    }

    return 0;
}