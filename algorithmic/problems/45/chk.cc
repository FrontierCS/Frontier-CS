#include <cmath>
#include <algorithm>

// Natural-log calibration above the original checker's 60-point threshold.
// Keep validation and low scores; an exact zero minimization cost earns 100.
static double natural_log_score(double old_points, long double value,
                                long double anchor, bool minimize) {
    if (minimize && value == 0.0L) return 100.0;
    if (old_points <= 60.0 || !(value > 0.0L) || !(anchor > 0.0L))
        return old_points;
    const long double delta = minimize ? std::log(anchor) - std::log(value)
                                       : std::log(value) - std::log(anchor);
    return (double)std::min(100.0L, 60.0L + delta);
}


#include "testlib.h"
#include <bits/stdc++.h>
using namespace std;
struct Graph { int n, m, k; double eps; vector<int> head, to, nxt; };
Graph readInput(InStream& inf) {
    Graph G; G.n = inf.readInt(); G.m = inf.readInt(); G.k = inf.readInt(); G.eps = inf.readDouble();
    if (G.k < 2) quitf(_fail, "k must be >= 2");
    if ((G.k & (G.k - 1)) != 0) quitf(_fail, "k must be a power of two");
    vector<vector<int>> adj(G.n);
    unordered_set<long long> seen; seen.reserve((size_t)G.m * 2);
    auto key = [&](int a,int b)->long long { return ((long long)min(a,b)<<32) ^ (unsigned)max(a,b); };
    for (int i=0;i<G.m;++i){ int u=inf.readInt(1,G.n)-1, v=inf.readInt(1,G.n)-1; if(u==v) continue;
        long long h=key(u,v); if (seen.insert(h).second){ adj[u].push_back(v); adj[v].push_back(u);} }
    long long m2=0; for(int i=0;i<G.n;++i) m2+=adj[i].size();
    G.head.assign(G.n,-1); G.to.reserve((size_t)m2); G.nxt.reserve((size_t)m2);
    int ptr=0; for(int u=0;u<G.n;++u){ for(int v:adj[u]){ G.to.push_back(v); G.nxt.push_back(G.head[u]); G.head[u]=ptr++; } }
    G.m=(int)(m2/2); return G;
}
long long edgeCut(const Graph& G, const vector<int>& part) {
    long long cut=0; for(int u=0;u<G.n;++u){ for(int e=G.head[u];e!=-1;e=G.nxt[e]){ int v=G.to[e]; if(u<v && part[u]!=part[v]) ++cut; } } return cut; }
long long commVolume(const Graph& G, const vector<int>& part) {
    int k=G.k; vector<int> seen(k,-1); vector<long long> sums(k,0);
    for(int v=0;v<G.n;++v){ int pv=part[v]; int mark=v; int cnt=0;
        for(int e=G.head[v];e!=-1;e=G.nxt[e]){ int u=G.to[e]; int pu=part[u];
            if(pu!=pv && seen[pu]!=mark){ seen[pu]=mark; ++cnt; } }
        sums[pv]+=cnt; }
    long long mx=0; for(int p=0;p<k;++p) mx=max(mx,sums[p]); return mx;
}
int maxAllowedSize(int n,int k,double eps){ int ce=(n+k-1)/k; return (int)floor((1.0+eps)*ce + 1e-12); }
int main(int argc,char* argv[]){
    registerTestlibCmd(argc, argv);
    Graph G=readInput(inf);
    vector<int> part(G.n);
    for(int i=0;i<G.n;++i){ if (ouf.seekEof()) quitf(_pe,"Expected %d labels, got %d",G.n,i);
        long long lab=ouf.readLong(); if(lab<1||lab>G.k) quitf(_wa,"Label %lld out of [1..%d] at %d",lab,G.k,i+1); part[i]=(int)(lab-1); }
    vector<int> sz(G.k,0); for(int x:part) ++sz[x]; int cap=maxAllowedSize(G.n,G.k,G.eps);
    for(int p=0;p<G.k;++p){ if(sz[p]>cap) quitf(_wa,"Balance violated: part %d has size %d > %d",p+1,sz[p],cap); }
    long long myEC=edgeCut(G,part), myCV=commVolume(G,part);
    long long bestEC=ans.readLong(), bestCV=ans.readLong(), baseEC=ans.readLong(), baseCV=ans.readLong();
    auto norm=[&](long long best,long long base,long long val){
        if (val == 0) return 1.0;
        if(base<=best) return (val<=best)?1.0:0.0;
        const long double den = (long double)base - best;
        const long double r = ((long double)base - val) / den;
        const double original_points = (double)(100.0L * std::clamp(r, 0.0L, 1.0L));
        const long double cost_anchor = 0.4L * base + 0.6L * best;
        return natural_log_score(original_points, val, cost_anchor, true) / 100.0; };
    double sEC=norm(bestEC,baseEC,myEC), sCV=norm(bestCV,baseCV,myCV), score=0.5*(sEC+sCV);
    quitp(score, "EC=%lld (best=%lld base=%lld), CV=%lld (best=%lld base=%lld). Ratio: %.12f RatioUnbounded: %.12f", myEC,bestEC,baseEC,myCV,bestCV,baseCV,score,score);
}
