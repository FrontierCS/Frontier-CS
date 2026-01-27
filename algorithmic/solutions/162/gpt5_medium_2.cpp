#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    const int N = 30;
    const int T = N*(N+1)/2; // 465
    vector<int> base(N+1,0);
    for(int i=1;i<=N;i++) base[i]=base[i-1]+i;
    auto idOf = [&](int x,int y){ return base[x]+y; };
    vector<pair<int,int>> coord(T);
    for(int x=0;x<N;x++){
        for(int y=0;y<=x;y++){
            int id = idOf(x,y);
            coord[id]={x,y};
        }
    }
    vector<int> val(T);
    for(int x=0;x<N;x++){
        for(int y=0;y<=x;y++){
            int id = idOf(x,y);
            cin >> val[id];
        }
    }
    // parents and children
    vector<array<int,2>> parents(T, array<int,2>{-1,-1});
    vector<array<int,2>> children(T, array<int,2>{-1,-1});
    for(int x=0;x<N;x++){
        for(int y=0;y<=x;y++){
            int id=idOf(x,y);
            int p0=-1,p1=-1;
            if(x>0){
                if(y-1>=0) p0=idOf(x-1,y-1);
                if(y<=x-1) p1=idOf(x-1,y);
            }
            parents[id][0]=p0; parents[id][1]=p1;
            int c0=-1,c1=-1;
            if(x+1<N){
                c0=idOf(x+1,y);
                c1=idOf(x+1,y+1);
            }
            children[id][0]=c0; children[id][1]=c1;
        }
    }
    // adjacency pairs (undirected) for allowed swaps (6-neighborhood)
    vector<pair<int,int>> adjPairs;
    adjPairs.reserve(T*3);
    for(int x=0;x<N;x++){
        for(int y=0;y<=x;y++){
            int id=idOf(x,y);
            auto addNeighbor=[&](int nx,int ny){
                if(nx<0||nx>=N) return;
                if(ny<0||ny>nx) return;
                int nid=idOf(nx,ny);
                if(nid>id) adjPairs.emplace_back(id,nid);
            };
            addNeighbor(x-1,y-1);
            addNeighbor(x-1,y);
            addNeighbor(x,y-1);
            addNeighbor(x,y+1);
            addNeighbor(x+1,y);
            addNeighbor(x+1,y+1);
        }
    }
    // initial E
    auto edgeViolation = [&](int p, int c)->int{
        if(p==-1||c==-1) return 0;
        return (val[p] > val[c]) ? 1 : 0;
    };
    long long E = 0;
    for(int x=0;x<N-1;x++){
        for(int y=0;y<=x;y++){
            int p=idOf(x,y);
            int c0=children[p][0], c1=children[p][1];
            E += edgeViolation(p,c0);
            E += edgeViolation(p,c1);
        }
    }
    // function to compute local delta for swapping a and b
    auto deltaSwap = [&](int a, int b)->int{
        int eP[16], eC[16]; int m=0;
        auto addEdgeU = [&](int p,int c){
            if(p==-1||c==-1) return;
            for(int i=0;i<m;i++){
                if(eP[i]==p && eC[i]==c) return;
            }
            eP[m]=p; eC[m]=c; m++;
        };
        // edges incident to a
        int c0=children[a][0], c1=children[a][1];
        addEdgeU(a,c0); addEdgeU(a,c1);
        int p0=parents[a][0], p1=parents[a][1];
        addEdgeU(p0,a); addEdgeU(p1,a);
        // edges incident to b
        c0=children[b][0]; c1=children[b][1];
        addEdgeU(b,c0); addEdgeU(b,c1);
        p0=parents[b][0]; p1=parents[b][1];
        addEdgeU(p0,b); addEdgeU(p1,b);
        int before=0, after=0;
        int va = val[a], vb = val[b];
        for(int i=0;i<m;i++){
            int p=eP[i], c=eC[i];
            before += (val[p] > val[c]) ? 1 : 0;
            int vp = (p==a ? vb : (p==b ? va : val[p]));
            int vc = (c==a ? vb : (c==b ? va : val[c]));
            after += (vp > vc) ? 1 : 0;
        }
        return after - before;
    };
    vector<array<int,4>> ops;
    ops.reserve(10000);
    // Main loop
    while((int)ops.size() < 10000) {
        if(E==0) break;
        int bestIdx = -1;
        int bestDelta = 0; // most negative
        int minNonNegIdx = -1;
        int minNonNegDelta = INT_MAX;
        for (int i=0;i<(int)adjPairs.size();i++){
            int a = adjPairs[i].first;
            int b = adjPairs[i].second;
            int d = deltaSwap(a,b);
            if (d < bestDelta) { bestDelta = d; bestIdx = i; }
            if (d >= 0 && d < minNonNegDelta) { minNonNegDelta = d; minNonNegIdx = i; }
        }
        if (bestIdx != -1) {
            int a = adjPairs[bestIdx].first;
            int b = adjPairs[bestIdx].second;
            swap(val[a], val[b]);
            E += bestDelta;
            auto [xa,ya]=coord[a];
            auto [xb,yb]=coord[b];
            ops.push_back({xa,ya,xb,yb});
        } else {
            if (minNonNegIdx != -1 && (int)ops.size() < 10000) {
                // perform a small "shake" move if it doesn't increase E too much
                if (minNonNegDelta <= 1) {
                    int a = adjPairs[minNonNegIdx].first;
                    int b = adjPairs[minNonNegIdx].second;
                    swap(val[a], val[b]);
                    E += minNonNegDelta;
                    auto [xa,ya]=coord[a];
                    auto [xb,yb]=coord[b];
                    ops.push_back({xa,ya,xb,yb});
                    continue;
                }
            }
            break;
        }
    }
    // Output
    cout << ops.size() << '\n';
    for (auto &op : ops) {
        cout << op[0] << ' ' << op[1] << ' ' << op[2] << ' ' << op[3] << '\n';
    }
    return 0;
}