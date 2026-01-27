#include <bits/stdc++.h>
using namespace std;

int n;

int ask(const vector<int>& s) {
    if ((int)s.size() <= 1) return 0;
    cout << "? " << s.size() << "\n";
    for (int i = 0; i < (int)s.size(); ++i) {
        if (i) cout << ' ';
        cout << s[i];
    }
    cout << "\n";
    cout.flush();
    int m;
    if (!(cin >> m)) exit(0);
    if (m == -1) exit(0);
    return m;
}

vector<int> with_union(const vector<int>& a, const vector<int>& b) {
    vector<int> res = a;
    res.insert(res.end(), b.begin(), b.end());
    return res;
}
vector<int> with_add(const vector<int>& a, int x) {
    vector<int> res = a;
    res.push_back(x);
    return res;
}

int findNeighborInSet(int v, vector<int> P) {
    while ((int)P.size() > 1) {
        int mid = (int)P.size() / 2;
        vector<int> L(P.begin(), P.begin() + mid);
        vector<int> R(P.begin() + mid, P.end());
        int eL = ask(L);
        vector<int> Lp = with_add(L, v);
        int eLv = ask(Lp);
        if (eLv > eL) {
            P = L;
        } else {
            P = R;
        }
    }
    return P[0];
}

int findVertexConnectingToRight(const vector<int>& Lfull, const vector<int>& R, int eR, int eRplus = -1) {
    // Find x in Lfull such that there is an edge between x and some node in R.
    // Uses crossEdges(C=R, X=subset of L): cross = e(R ∪ X) - e(R) - e(X)
    vector<int> L = Lfull;
    while ((int)L.size() > 1) {
        int mid = (int)L.size() / 2;
        vector<int> A(L.begin(), L.begin() + mid);
        vector<int> B(L.begin() + mid, L.end());
        int eA = ask(A);
        vector<int> RA = with_union(R, A);
        int eRA = ask(RA);
        int crossA = eRA - eR - eA;
        if (crossA > 0) {
            L = A;
        } else {
            L = B;
        }
    }
    return L[0];
}

int findNeighborWithinSubset(int x, vector<int> S) {
    while ((int)S.size() > 1) {
        int mid = (int)S.size() / 2;
        vector<int> L(S.begin(), S.begin() + mid);
        vector<int> R(S.begin() + mid, S.end());
        int eL = ask(L);
        vector<int> Lx = with_add(L, x);
        int eLx = ask(Lx);
        if (eLx > eL) {
            S = L;
        } else {
            S = R;
        }
    }
    return S[0];
}

pair<int,int> findEdgeInSet(vector<int> S) {
    // assumes ask(S) > 0
    while ((int)S.size() > 2) {
        int mid = (int)S.size() / 2;
        vector<int> L(S.begin(), S.begin() + mid);
        vector<int> R(S.begin() + mid, S.end());
        int eL = ask(L);
        if (eL > 0) {
            S = L;
            continue;
        }
        int eR = ask(R);
        if (eR > 0) {
            S = R;
            continue;
        }
        // All edges are crossing between L and R
        int eR0 = eR;
        int x = findVertexConnectingToRight(L, R, eR0);
        int y = findNeighborWithinSubset(x, R);
        return {x, y};
    }
    // size 2
    return {S[0], S[1]};
}

struct DSU {
    vector<int> p, r;
    DSU(int n=0) { init(n); }
    void init(int n) { p.resize(n+1); r.assign(n+1,0); iota(p.begin(), p.end(), 0); }
    int find(int x){ return p[x]==x?x:p[x]=find(p[x]); }
    bool unite(int a,int b){
        a=find(a); b=find(b);
        if(a==b) return false;
        if(r[a]<r[b]) swap(a,b);
        p[b]=a;
        if(r[a]==r[b]) r[a]++;
        return true;
    }
};

vector<int> getPath(int s, int t, const vector<vector<int>>& adj) {
    vector<int> par(n+1, -1);
    queue<int> q;
    q.push(s);
    par[s] = s;
    while (!q.empty()) {
        int u = q.front(); q.pop();
        if (u == t) break;
        for (int w: adj[u]) {
            if (par[w] == -1) {
                par[w] = u;
                q.push(w);
            }
        }
    }
    vector<int> path;
    if (par[t] == -1) return path;
    int cur = t;
    while (cur != par[cur]) {
        path.push_back(cur);
        cur = par[cur];
    }
    path.push_back(cur);
    reverse(path.begin(), path.end());
    return path;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    if (!(cin >> n)) return 0;

    vector<vector<int>> adj(n+1);
    DSU dsu(n);

    vector<int> P; // processed set
    int eP = 0; // edges inside P

    for (int v = 1; v <= n; ++v) {
        if (P.empty()) {
            // edges({v}) == 0, we can skip asking
            P.push_back(v);
            eP = 0;
            continue;
        }
        vector<int> Pplus = with_add(P, v);
        int ePplus = ask(Pplus);
        int inc = ePplus - eP; // edges between v and P
        if (inc > 0) {
            int u = findNeighborInSet(v, P);
            adj[v].push_back(u);
            adj[u].push_back(v);
            dsu.unite(u, v);
        }
        P.push_back(v);
        eP = ePplus;
    }

    // Connect components by finding edges between them
    while (true) {
        unordered_map<int, vector<int>> comps;
        for (int i = 1; i <= n; ++i) comps[dsu.find(i)].push_back(i);
        if ((int)comps.size() == 1) break;
        // pick one component
        auto it = comps.begin();
        vector<int> C = it->second;
        vector<int> U;
        for (auto &kv : comps) {
            if (kv.first == it->first) continue;
            for (int x : kv.second) U.push_back(x);
        }
        int eC = ask(C);
        // find a vertex in U connected to C
        int eU = ask(U);
        vector<int> CU = with_union(C, U);
        int eCU = ask(CU);
        int crossCU = eCU - eC - eU;
        if (crossCU <= 0) {
            // Should not happen if the original graph is connected
            // But to be safe, try another component
            auto it2 = next(it);
            if (it2 == comps.end()) break;
        }
        int x = findVertexConnectingToRight(U, C, eC);
        int y = findNeighborWithinSubset(x, C);
        if (dsu.unite(x, y)) {
            adj[x].push_back(y);
            adj[y].push_back(x);
        }
    }

    // Try to 2-color graph and detect odd cycle within found edges
    vector<int> color(n+1, -1);
    for (int s = 1; s <= n; ++s) {
        if (color[s] != -1) continue;
        queue<int> q;
        color[s] = 0;
        q.push(s);
        while (!q.empty()) {
            int u = q.front(); q.pop();
            for (int w : adj[u]) {
                if (color[w] == -1) {
                    color[w] = 1 - color[u];
                    q.push(w);
                } else if (color[w] == color[u]) {
                    // Found odd cycle within known edges
                    vector<int> path = getPath(u, w, adj);
                    if (path.empty()) {
                        // fallback: simple cycle u-w with path via BFS (shouldn't happen)
                        path.push_back(u);
                        path.push_back(w);
                    }
                    cout << "N " << path.size() << "\n";
                    for (int i = 0; i < (int)path.size(); ++i) {
                        if (i) cout << ' ';
                        cout << path[i];
                    }
                    cout << "\n";
                    cout.flush();
                    return 0;
                }
            }
        }
    }

    vector<int> A, B;
    for (int i = 1; i <= n; ++i) {
        if (color[i] == 0) A.push_back(i);
        else B.push_back(i);
    }

    int eA = ask(A);
    if (eA > 0) {
        auto pr = findEdgeInSet(A);
        int x = pr.first, y = pr.second;
        vector<int> path = getPath(x, y, adj);
        cout << "N " << path.size() << "\n";
        for (int i = 0; i < (int)path.size(); ++i) {
            if (i) cout << ' ';
            cout << path[i];
        }
        cout << "\n";
        cout.flush();
        return 0;
    }
    int eB = ask(B);
    if (eB > 0) {
        auto pr = findEdgeInSet(B);
        int x = pr.first, y = pr.second;
        vector<int> path = getPath(x, y, adj);
        cout << "N " << path.size() << "\n";
        for (int i = 0; i < (int)path.size(); ++i) {
            if (i) cout << ' ';
            cout << path[i];
        }
        cout << "\n";
        cout.flush();
        return 0;
    }

    cout << "Y " << A.size() << "\n";
    for (int i = 0; i < (int)A.size(); ++i) {
        if (i) cout << ' ';
        cout << A[i];
    }
    cout << "\n";
    cout.flush();
    return 0;
}