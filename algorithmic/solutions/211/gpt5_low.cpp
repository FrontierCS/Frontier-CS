#include <bits/stdc++.h>
using namespace std;

struct Node {
    int id;
    int x, y;
    char t;
};

struct Edge {
    int u, v;
    double w;
    bool operator<(Edge const& other) const { return w < other.w; }
};

struct DSU {
    vector<int> p, r;
    vector<char> hasRobot;
    DSU(int n, const vector<char>& isRobot) : p(n), r(n,0), hasRobot(isRobot) {
        iota(p.begin(), p.end(), 0);
    }
    int find(int a){ return p[a]==a ? a : p[a]=find(p[a]); }
    bool unite(int a, int b, int &robotComps){
        a=find(a); b=find(b);
        if(a==b) return false;
        if(r[a]<r[b]) swap(a,b);
        p[b]=a;
        if(r[a]==r[b]) r[a]++;
        if(hasRobot[a] && hasRobot[b]) robotComps--;
        hasRobot[a] = hasRobot[a] || hasRobot[b];
        return true;
    }
};

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N, K;
    if(!(cin >> N >> K)) return 0;
    int total = N + K;
    vector<Node> nodes(total);
    vector<int> robotsIdx;
    vector<int> relaysIdx;
    for(int i=0;i<total;i++){
        int id,x,y; string ts;
        cin >> id >> x >> y >> ts;
        nodes[i] = {id,x,y,ts[0]};
        if(nodes[i].t=='R' || nodes[i].t=='S') robotsIdx.push_back(i);
        else relaysIdx.push_back(i);
    }
    int Rn = (int)robotsIdx.size();
    int Cn = (int)relaysIdx.size();

    vector<Edge> edges;
    edges.reserve( (long long)Rn*(Rn-1)/2 + (long long)Rn*Cn );

    auto sqdist = [&](int i, int j)->long long{
        long long dx = nodes[i].x - nodes[j].x;
        long long dy = nodes[i].y - nodes[j].y;
        return dx*dx + dy*dy;
    };

    // robot-robot edges
    for(int a=0;a<Rn;a++){
        int i = robotsIdx[a];
        for(int b=a+1;b<Rn;b++){
            int j = robotsIdx[b];
            double factor = (nodes[i].t=='S' || nodes[j].t=='S') ? 0.8 : 1.0;
            double w = (double)sqdist(i,j) * factor;
            edges.push_back({i,j,w});
        }
    }
    // relay-robot edges
    for(int ci=0; ci<Cn; ci++){
        int c = relaysIdx[ci];
        for(int ri=0; ri<Rn; ri++){
            int r = robotsIdx[ri];
            double w = (double)sqdist(c,r) * 1.0;
            edges.push_back({c,r,w});
        }
    }

    sort(edges.begin(), edges.end());

    vector<char> isRobot(total, 0);
    for(int idx: robotsIdx) isRobot[idx]=1;
    DSU dsu(total, isRobot);
    int robotComps = Rn;

    vector<pair<int,int>> chosen;
    chosen.reserve(Rn + Cn);

    for(const auto& e: edges){
        if(robotComps==1) break;
        if(dsu.unite(e.u, e.v, robotComps)){
            chosen.emplace_back(e.u, e.v);
        }
    }

    // Determine used relays
    unordered_set<int> usedRelayIdxSet;
    usedRelayIdxSet.reserve(Cn*2+1);
    for(auto &pr : chosen){
        int u = pr.first, v = pr.second;
        if(nodes[u].t=='C') usedRelayIdxSet.insert(u);
        if(nodes[v].t=='C') usedRelayIdxSet.insert(v);
    }
    vector<int> usedRelayIDs;
    usedRelayIDs.reserve(usedRelayIdxSet.size());
    for(int idx : usedRelayIdxSet) usedRelayIDs.push_back(nodes[idx].id);
    sort(usedRelayIDs.begin(), usedRelayIDs.end());

    // Output
    if(usedRelayIDs.empty()){
        cout << "#\n";
    }else{
        for(size_t i=0;i<usedRelayIDs.size();i++){
            if(i) cout << "#";
            cout << usedRelayIDs[i];
        }
        cout << "\n";
    }
    for(size_t i=0;i<chosen.size();i++){
        if(i) cout << "#";
        cout << nodes[chosen[i].first].id << "-" << nodes[chosen[i].second].id;
    }
    if(chosen.empty()) cout << "";
    cout << "\n";
    return 0;
}