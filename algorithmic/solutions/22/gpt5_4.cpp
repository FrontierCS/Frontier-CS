#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N;
    if(!(cin >> N)) return 0;
    vector<vector<int>> g(N+1);
    for (int i = 2; i <= N; ++i) {
        int p; cin >> p;
        g[p].push_back(i);
        g[i].push_back(p);
    }
    // Compute parent using DFS from 1
    vector<int> parent(N+1, 0);
    vector<int> orderDFS;
    orderDFS.reserve(N);
    {
        vector<int> st; st.push_back(1);
        parent[1] = 0;
        while (!st.empty()) {
            int v = st.back(); st.pop_back();
            orderDFS.push_back(v);
            for (int u : g[v]) if (u != parent[v]) {
                parent[u] = v;
                st.push_back(u);
            }
        }
    }
    // Find leaves (degree 1 in tree)
    vector<int> deg(N+1, 0);
    for (int v = 1; v <= N; ++v) deg[v] = (int)g[v].size();
    vector<int> leaves;
    for (int v = 1; v <= N; ++v) if (deg[v] == 1) leaves.push_back(v);
    sort(leaves.begin(), leaves.end());
    int k = (int)leaves.size();
    // Elimination order and Nplus sets
    vector<int> elim_order; elim_order.reserve(N);
    vector<vector<int>> Nplus(N+1);
    int s = leaves[0]; // choose smallest leaf as 'v1'
    // Step 1: eliminate leaves v2..vk in increasing order
    for (int i = 1; i < k; ++i) {
        int v = leaves[i];
        // later neighbors at this time: parent[v], s, and next leaf if exists
        if (parent[v] != 0) Nplus[v].push_back(parent[v]);
        Nplus[v].push_back(s);
        if (i+1 < k) Nplus[v].push_back(leaves[i+1]);
        // dedup will be done later on bag creation
        elim_order.push_back(v);
    }
    // Step 2: eliminate remaining vertices by peeling the tree leaves
    vector<char> alive(N+1, 1);
    for (int i = 1; i < k; ++i) alive[leaves[i]] = 0; // removed in step 1
    vector<int> deg_rem(N+1, 0);
    for (int v = 1; v <= N; ++v) if (alive[v]) {
        int cnt = 0;
        for (int u : g[v]) if (alive[u]) ++cnt;
        deg_rem[v] = cnt;
    }
    deque<int> q;
    for (int v = 1; v <= N; ++v) if (alive[v] && deg_rem[v] <= 1) q.push_back(v);
    while (!q.empty()) {
        int v = q.front(); q.pop_front();
        if (!alive[v]) continue;
        // record its unique alive neighbor if exists
        int lastNeighbor = -1;
        for (int u : g[v]) if (alive[u]) { lastNeighbor = u; break; }
        if (lastNeighbor != -1) Nplus[v].push_back(lastNeighbor);
        elim_order.push_back(v);
        // remove v
        alive[v] = 0;
        for (int u : g[v]) if (alive[u]) {
            if (--deg_rem[u] <= 1) q.push_back(u);
        }
    }
    // sanity: elim_order size should be N
    if ((int)elim_order.size() != N) {
        // Fallback: in unlikely case, just output a trivial valid decomposition (K=N, bags of size up to 4)
        // But given the problem guarantees, this shouldn't happen.
    }
    // positions
    vector<int> pos(N+1, 0);
    for (int i = 0; i < N; ++i) pos[elim_order[i]] = i+1; // 1-based
    // Build bags
    int K = N;
    vector<vector<int>> bags(K+1);
    for (int i = 1; i <= K; ++i) {
        int v = elim_order[i-1];
        vector<int> elems;
        elems.push_back(v);
        for (int u : Nplus[v]) elems.push_back(u);
        // dedup
        sort(elems.begin(), elems.end());
        elems.erase(unique(elems.begin(), elems.end()), elems.end());
        bags[i] = move(elems);
    }
    // Build tree edges among bags: parent is minimal later neighbor in pos
    vector<pair<int,int>> treeEdges;
    treeEdges.reserve(K-1);
    for (int i = 1; i <= K; ++i) {
        int v = elim_order[i-1];
        int bestBag = -1;
        int bestPos = INT_MAX;
        for (int u : Nplus[v]) {
            if (pos[u] > pos[v] && pos[u] < bestPos) {
                bestPos = pos[u];
                bestBag = pos[u]; // bag index equals position
            }
        }
        if (bestBag != -1) {
            treeEdges.emplace_back(i, bestBag);
        }
    }
    // Output
    cout << K << "\n";
    for (int i = 1; i <= K; ++i) {
        cout << (int)bags[i].size();
        for (int x : bags[i]) cout << " " << x;
        cout << "\n";
    }
    // Ensure we have exactly K-1 edges. If not (shouldn't happen), connect remaining arbitrarily.
    if ((int)treeEdges.size() < K-1) {
        vector<int> roots;
        vector<int> degBag(K+1, 0);
        vector<vector<int>> adjB(K+1);
        for (auto &e : treeEdges) {
            adjB[e.first].push_back(e.second);
            adjB[e.second].push_back(e.first);
            degBag[e.first]++; degBag[e.second]++;
        }
        vector<int> comp(K+1, -1);
        int cid = 0;
        for (int i = 1; i <= K; ++i) if (comp[i] == -1) {
            // BFS
            queue<int> qq; qq.push(i); comp[i] = cid;
            while (!qq.empty()) {
                int v = qq.front(); qq.pop();
                for (int u : adjB[v]) if (comp[u] == -1) {
                    comp[u] = cid; qq.push(u);
                }
            }
            roots.push_back(i);
            cid++;
        }
        for (int i = 1; i < (int)roots.size(); ++i) {
            treeEdges.emplace_back(roots[0], roots[i]);
        }
    }
    for (auto &e : treeEdges) cout << e.first << " " << e.second << "\n";
    return 0;
}