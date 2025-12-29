#include <iostream>
#include <vector>
#include <algorithm>
#include <stack>
using namespace std;

struct DSU {
    vector<int> parent, size;
    DSU(int n) {
        parent.resize(n);
        size.resize(n, 1);
        for (int i=0; i<n; i++) parent[i]=i;
    }
    int find(int x) {
        if (parent[x]!=x) parent[x]=find(parent[x]);
        return parent[x];
    }
    void unite(int x, int y) {
        x=find(x); y=find(y);
        if (x==y) return;
        if (size[x] < size[y]) swap(x,y);
        parent[y]=x;
        size[x]+=size[y];
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M, H;
    cin >> N >> M >> H;
    vector<int> A(N);
    for (int i=0; i<N; i++) cin >> A[i];
    vector<pair<int,int>> edges(M);
    for (int i=0; i<M; i++) {
        int u,v;
        cin >> u >> v;
        edges[i] = {u,v};
    }
    // read coordinates (unused)
    for (int i=0; i<N; i++) {
        int x,y;
        cin >> x >> y;
    }

    // Initialize
    vector<int> parent(N, -1);
    vector<vector<int>> children(N);
    vector<int> depth(N, 0);
    DSU dsu(N);
    vector<int> comp_root(N);
    vector<int> comp_max_depth(N, 0);
    vector<long long> comp_total_beauty(N);
    for (int i=0; i<N; i++) {
        comp_root[i] = i;
        comp_total_beauty[i] = A[i];
    }

    bool updated = true;
    while (updated) {
        updated = false;
        long long best_gain = 0;
        int best_r = -1, best_x = -1;
        int best_ru = -1, best_rv = -1;
        int best_delta = 0;

        for (const auto& e : edges) {
            int u = e.first, v = e.second;
            int ru = dsu.find(u);
            int rv = dsu.find(v);
            if (ru == rv) continue;

            // if u is root
            if (parent[u] == -1) {
                int r = u;
                int x = v;
                int delta = depth[x] + 1 - depth[r];
                if (delta > 0 && comp_max_depth[ru] + delta <= H) {
                    long long gain = delta * comp_total_beauty[ru];
                    if (gain > best_gain) {
                        best_gain = gain;
                        best_r = r; best_x = x; best_delta = delta;
                        best_ru = ru; best_rv = rv;
                    }
                }
            }
            // if v is root
            if (parent[v] == -1) {
                int r = v;
                int x = u;
                int delta = depth[x] + 1 - depth[r];
                if (delta > 0 && comp_max_depth[rv] + delta <= H) {
                    long long gain = delta * comp_total_beauty[rv];
                    if (gain > best_gain) {
                        best_gain = gain;
                        best_r = r; best_x = x; best_delta = delta;
                        best_ru = rv; best_rv = ru;
                    }
                }
            }
        }

        if (best_gain > 0) {
            updated = true;
            // attach best_r to best_x
            // update depths in subtree of best_r
            stack<int> st;
            st.push(best_r);
            while (!st.empty()) {
                int u = st.top(); st.pop();
                depth[u] += best_delta;
                for (int c : children[u]) {
                    st.push(c);
                }
            }
            // set parent and children
            parent[best_r] = best_x;
            children[best_x].push_back(best_r);

            // merge components: best_ru into best_rv
            int rep_ru = best_ru;
            int rep_rv = best_rv;
            // Update data for rep_rv
            comp_total_beauty[rep_rv] += comp_total_beauty[rep_ru];
            comp_max_depth[rep_rv] = max(comp_max_depth[rep_rv], comp_max_depth[rep_ru] + best_delta);
            // union in DSU
            dsu.parent[rep_ru] = rep_rv;
            dsu.size[rep_rv] += dsu.size[rep_ru];
        }
    }

    // Output parent array
    for (int i=0; i<N; i++) {
        cout << parent[i];
        if (i < N-1) cout << " ";
    }
    cout << endl;

    return 0;
}