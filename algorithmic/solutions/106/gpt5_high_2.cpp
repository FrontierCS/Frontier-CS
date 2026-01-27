#include <bits/stdc++.h>
using namespace std;

struct DSU {
    int n;
    vector<int> p, r, xr; // xr[x]: parity from x to parent
    DSU(int n=0): n(n), p(n+1), r(n+1,0), xr(n+1,0) {
        for(int i=0;i<=n;i++) p[i]=i;
    }
    pair<int,int> findp(int x){
        if(p[x]==x) return {x,0};
        auto pr = findp(p[x]);
        xr[x] ^= pr.second;
        p[x] = pr.first;
        return {p[x], xr[x]};
    }
    // w = parity(u) ^ parity(v), for edge u-v we want w=1
    bool unite(int a, int b, int w){
        auto pa = findp(a);
        auto pb = findp(b);
        int ra = pa.first, rb = pb.first;
        int xa = pa.second, xb = pb.second;
        if(ra==rb){
            // xa ^ xb should equal w in consistent case; ignore otherwise
            return ( (xa ^ xb) == w );
        }
        if(r[ra] < r[rb]){
            p[ra] = rb;
            xr[ra] = xa ^ xb ^ w;
        } else if(r[ra] > r[rb]){
            p[rb] = ra;
            xr[rb] = xa ^ xb ^ w;
        } else {
            p[ra] = rb;
            xr[ra] = xa ^ xb ^ w;
            r[rb]++;
        }
        return true;
    }
    int get_parity(int x){
        return findp(x).second & 1;
    }
};

int n;

int ask(const vector<int>& s){
    int k = (int)s.size();
    if(k <= 0){
        // According to problem, k must be >= 1; avoid invalid query.
        // Should not happen.
        return 0;
    }
    cout << "? " << k << endl;
    for(int i=0;i<k;i++){
        if(i) cout << ' ';
        cout << s[i];
    }
    cout << endl;
    cout.flush();
    int res;
    if(!(cin >> res)){
        exit(0);
    }
    if(res == -1){
        exit(0);
    }
    return res;
}

vector<int> merge_sets(const vector<int>& a, const vector<int>& b){
    vector<int> r;
    r.reserve(a.size()+b.size());
    for(int x: a) r.push_back(x);
    for(int x: b) r.push_back(x);
    return r;
}

// Find a vertex in A that has at least one edge to B.
// eB is edges(B). Assumes there exists at least one crossing edge.
int find_vertex_with_edge_to(const vector<int>& A, const vector<int>& B, int eB){
    vector<int> cur = A;
    while(cur.size() > 1){
        int m = (int)cur.size();
        int h = m/2;
        vector<int> H(cur.begin(), cur.begin()+h);
        vector<int> T(cur.begin()+h, cur.end());
        int eH = ask(H);
        vector<int> HB = merge_sets(H, B);
        int eHB = ask(HB);
        int cross = eHB - eH - eB;
        if(cross > 0){
            cur = H;
        } else {
            cur = T;
        }
    }
    return cur[0];
}

// Find a neighbor of v inside set S (S non-empty, and v has at least one neighbor in S)
int find_neighbor_in_set(int v, const vector<int>& S){
    vector<int> cur = S;
    while(cur.size() > 1){
        int m = (int)cur.size();
        int h = m/2;
        vector<int> H(cur.begin(), cur.begin()+h);
        vector<int> T(cur.begin()+h, cur.end());
        vector<int> Hv = H; Hv.push_back(v);
        int eHv = ask(Hv);
        int eH = ask(H);
        int deg = eHv - eH;
        if(deg > 0){
            cur = H;
        } else {
            cur = T;
        }
    }
    return cur[0];
}

// Find an edge inside set S (assumes e(S) > 0)
pair<int,int> find_edge_inside_set(const vector<int>& S){
    vector<int> cur = S;
    while(true){
        if(cur.size() == 2){
            // verify they are connected
            int e2 = ask(cur);
            if(e2 > 0) return {cur[0], cur[1]};
            // Should not happen if invariant e(cur)>0 holds.
        }
        int m = (int)cur.size();
        int h = m/2;
        vector<int> A(cur.begin(), cur.begin()+h);
        vector<int> B(cur.begin()+h, cur.end());
        int eA = ask(A);
        if(eA > 0){
            cur = A;
            continue;
        }
        int eB = ask(B);
        if(eB > 0){
            cur = B;
            continue;
        }
        // No internal edges in A or B, so edges must cross between A and B
        // Find a vertex a in A that connects to B
        int a = find_vertex_with_edge_to(A, B, eB);
        // Find neighbor of a in B
        int b = find_neighbor_in_set(a, B);
        return {a, b};
    }
}

// Build a spanning tree to ensure connectivity
void build_spanning_tree(vector<vector<int>>& tree, DSU& dsu){
    vector<int> P; P.reserve(n);
    vector<int> U; U.reserve(n);
    for(int i=2;i<=n;i++) U.push_back(i);
    P.push_back(1);
    int eP = ask(P); // should be 0
    while(!U.empty()){
        // Find a vertex v in U that has an edge to P
        int v = find_vertex_with_edge_to(U, P, eP);
        // Find neighbor u in P
        int u = find_neighbor_in_set(v, P);
        // Add edge u-v
        tree[u].push_back(v);
        tree[v].push_back(u);
        dsu.unite(u, v, 1);
        // Move v from U to P
        P.push_back(v);
        auto it = find(U.begin(), U.end(), v);
        if(it != U.end()) U.erase(it);
        // Update eP for new P
        eP = ask(P);
    }
}

vector<int> get_path_in_tree(int src, int dst, const vector<vector<int>>& tree){
    vector<int> prev(n+1, -1);
    queue<int> q;
    q.push(src);
    prev[src] = -2;
    while(!q.empty()){
        int u = q.front(); q.pop();
        if(u == dst) break;
        for(int w: tree[u]){
            if(prev[w] == -1){
                prev[w] = u;
                q.push(w);
            }
        }
    }
    vector<int> path;
    int cur = dst;
    while(cur != -2){
        path.push_back(cur);
        cur = prev[cur];
    }
    reverse(path.begin(), path.end());
    return path;
}

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    if(!(cin >> n)) return 0;

    DSU dsu(n);
    vector<vector<int>> tree(n+1);

    // Build connected spanning tree using queries
    build_spanning_tree(tree, dsu);

    // Derive coloring from DSU parity
    vector<int> side0, side1;
    for(int i=1;i<=n;i++){
        int c = dsu.get_parity(i);
        if(c==0) side0.push_back(i);
        else side1.push_back(i);
    }

    auto get_edges_in_set = [&](const vector<int>& S)->int{
        if(S.empty()) return 0;
        return ask(S);
    };

    int e0 = get_edges_in_set(side0);
    int e1 = get_edges_in_set(side1);

    if(e0 == 0 && e1 == 0){
        cout << "Y " << side0.size() << endl;
        for(size_t i=0;i<side0.size();i++){
            if(i) cout << ' ';
            cout << side0[i];
        }
        cout << endl;
        cout.flush();
        return 0;
    } else {
        vector<int> S = (e0 > 0 ? side0 : side1);
        pair<int,int> ed = find_edge_inside_set(S);
        int u = ed.first, v = ed.second;
        vector<int> cycle = get_path_in_tree(u, v, tree); // path u..v
        cout << "N " << cycle.size() << endl;
        for(size_t i=0;i<cycle.size();i++){
            if(i) cout << ' ';
            cout << cycle[i];
        }
        cout << endl;
        cout.flush();
        return 0;
    }
}