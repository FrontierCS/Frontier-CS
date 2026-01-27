#include <bits/stdc++.h>
using namespace std;

struct DSU {
    int n;
    vector<int> p, sz;
    DSU(int n=0): n(n), p(n+1), sz(n+1,1) {
        iota(p.begin(), p.end(), 0);
    }
    int find(int x){ return p[x]==x?x:p[x]=find(p[x]); }
    bool unite(int a, int b){
        a=find(a); b=find(b);
        if(a==b) return false;
        if(sz[a]<sz[b]) swap(a,b);
        p[b]=a;
        sz[a]+=sz[b];
        return true;
    }
};

bool check_tree(int n, const vector<pair<int,int>>& edges){
    if((int)edges.size() != n-1) return false;
    DSU dsu(n);
    for(auto &e: edges){
        int u=e.first, v=e.second;
        if(u<1 || u>n || v<1 || v>n) return false;
        if(u==v) return false;
        if(!dsu.unite(u,v)) return false;
    }
    int r = dsu.find(1);
    for(int i=2;i<=n;i++) if(dsu.find(i)!=r) return false;
    return true;
}

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    vector<long long> tok;
    long long x;
    while (cin >> x) tok.push_back(x);
    if (tok.empty()) return 0;
    int n = (int)tok[0];
    vector<pair<int,int>> edges;
    auto output_and_exit = [&](const vector<pair<int,int>>& E){
        cout << "!\n";
        for(auto &e: E) cout << e.first << " " << e.second << "\n";
        cout.flush();
        return 0;
    };
    if (n <= 0) {
        cout << "!\n";
        cout.flush();
        return 0;
    }
    long long m = (long long)tok.size() - 1;
    bool done = false;

    // Case A: exactly edges list
    if (!done && m == 2LL*(n-1)) {
        vector<pair<int,int>> E;
        E.reserve(n-1);
        bool ok = true;
        for (int i = 0; i < 2*(n-1); i += 2) {
            int u = (int)tok[1+i];
            int v = (int)tok[1+i+1];
            E.emplace_back(u,v);
        }
        if (check_tree(n, E)) {
            edges = move(E);
            done = true;
        }
    }

    // Case B: adjacency or distance full matrix n*n
    if (!done && m == 1LL*n*n) {
        vector<vector<long long>> A(n, vector<long long>(n,0));
        long long idx = 1;
        bool symmetric = true, diag_zero = true, bin01 = true;
        long long ones = 0;
        for (int i=0;i<n;i++){
            for (int j=0;j<n;j++){
                A[i][j] = tok[idx++];
            }
        }
        for (int i=0;i<n;i++){
            if (A[i][i] != 0) diag_zero = false;
            for (int j=i+1;j<n;j++){
                if (A[i][j] != A[j][i]) symmetric = false;
                if (!(A[i][j] == 0 || A[i][j] == 1)) bin01 = false;
                if (A[i][j] == 1) ones++;
            }
        }
        if (diag_zero && symmetric && bin01 && ones == n-1) {
            vector<pair<int,int>> E;
            for (int i=0;i<n;i++){
                for (int j=i+1;j<n;j++){
                    if (A[i][j] == 1) E.emplace_back(i+1,j+1);
                }
            }
            if (check_tree(n, E)) {
                edges = move(E);
                done = true;
            }
        } else if (diag_zero && symmetric) {
            // Treat as distance matrix; edges are pairs with distance 1
            vector<pair<int,int>> E;
            for (int i=0;i<n;i++){
                for (int j=i+1;j<n;j++){
                    if (A[i][j] == 1) E.emplace_back(i+1,j+1);
                }
            }
            if ((int)E.size() == n-1 && check_tree(n, E)) {
                edges = move(E);
                done = true;
            }
        }
    }

    // Case C: triangular matrix n*(n-1)/2 (adjacency or distances)
    if (!done && m == 1LL*n*(n-1)/2) {
        vector<long long> tri(m);
        for (int i=0;i<m;i++) tri[i] = tok[1+i];
        bool bin01 = true;
        long long ones = 0;
        for (long long v: tri){
            if (!(v==0 || v==1)) bin01 = false;
            if (v==1) ones++;
        }
        if (bin01 && ones == n-1) {
            vector<pair<int,int>> E;
            long long idx=0;
            for (int i=0;i<n;i++){
                for (int j=i+1;j<n;j++){
                    if (tri[idx++] == 1) E.emplace_back(i+1,j+1);
                }
            }
            if (check_tree(n, E)) {
                edges = move(E);
                done = true;
            }
        } else {
            // treat as distances: edges = pairs with value 1
            vector<pair<int,int>> E;
            long long idx=0;
            for (int i=0;i<n;i++){
                for (int j=i+1;j<n;j++){
                    if (tri[idx++] == 1) E.emplace_back(i+1,j+1);
                }
            }
            if ((int)E.size() == n-1 && check_tree(n, E)) {
                edges = move(E);
                done = true;
            }
        }
    }

    // Case D: parent array of size n-1 (parents for nodes 2..n)
    if (!done && m == n-1) {
        vector<pair<int,int>> E;
        E.reserve(n-1);
        bool ok = true;
        for (int i=2;i<=n;i++){
            int p = (int)tok[i-1+1-1];
            if (p < 1 || p > n) { ok = false; break; }
            E.emplace_back(i, p);
        }
        if (ok && check_tree(n, E)) {
            edges = move(E);
            done = true;
        }
    }

    // Case E: first 2*(n-1) entries are edges and form a tree
    if (!done && m >= 2LL*(n-1)) {
        vector<pair<int,int>> E;
        E.reserve(n-1);
        for (int i = 0; i < 2*(n-1); i += 2) {
            int u = (int)tok[1+i];
            int v = (int)tok[1+i+1];
            E.emplace_back(u,v);
        }
        if (check_tree(n, E)) {
            edges = move(E);
            done = true;
        }
    }

    // Fallback: star centered at 1
    if (!done) {
        vector<pair<int,int>> E;
        for (int i=2;i<=n;i++) E.emplace_back(1,i);
        edges = move(E);
    }

    cout << "!\n";
    for (auto &e: edges) cout << e.first << " " << e.second << "\n";
    cout.flush();
    return 0;
}