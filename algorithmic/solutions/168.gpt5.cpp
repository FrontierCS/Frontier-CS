#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M, H;
    if (!(cin >> N >> M >> H)) return 0;
    vector<int> A(N);
    for (int i = 0; i < N; i++) cin >> A[i];
    vector<pair<int,int>> edges(M);
    vector<vector<int>> g(N);
    for (int i = 0; i < M; i++) {
        int u, v; cin >> u >> v;
        edges[i] = {u, v};
        g[u].push_back(v);
        g[v].push_back(u);
    }
    // read coordinates (unused)
    vector<pair<int,int>> coord(N);
    for (int i = 0; i < N; i++) {
        int x, y; cin >> x >> y;
        coord[i] = {x, y};
    }

    // Precompute closed neighborhoods
    vector<vector<int>> closeNb(N);
    closeNb.reserve(N);
    for (int v = 0; v < N; v++) {
        closeNb[v].push_back(v);
        for (int to : g[v]) closeNb[v].push_back(to);
        sort(closeNb[v].begin(), closeNb[v].end());
        closeNb[v].erase(unique(closeNb[v].begin(), closeNb[v].end()), closeNb[v].end());
    }

    // Greedy weighted dominating set by cost-effectiveness: minimize A[u] / sum A[uncovered in N[u] U {u}]
    vector<char> covered(N, 0);
    vector<char> inC(N, 0);
    int coveredCnt = 0;
    const double EPS = 1e-9;
    while (coveredCnt < N) {
        int best = -1;
        double bestRatio = 1e100;
        int bestCovCnt = -1;
        long long bestCovWeight = -1;
        for (int u = 0; u < N; u++) {
            long long covWeight = 0;
            int covCnt = 0;
            for (int w : closeNb[u]) if (!covered[w]) {
                covWeight += A[w];
                covCnt++;
            }
            if (covCnt == 0) continue;
            double ratio = (double)A[u] / (double)(covWeight + EPS);
            if (ratio < bestRatio - 1e-15 ||
                (abs(ratio - bestRatio) <= 1e-15 && (covWeight > bestCovWeight ||
                 (covWeight == bestCovWeight && (covCnt > bestCovCnt ||
                  (covCnt == bestCovCnt && A[u] < (best == -1 ? INT_MAX : A[best]))))))) {
                best = u;
                bestRatio = ratio;
                bestCovCnt = covCnt;
                bestCovWeight = covWeight;
            }
        }
        if (best == -1) {
            // Fallback: choose any uncovered vertex itself
            for (int u = 0; u < N; u++) if (!covered[u]) { best = u; break; }
        }
        inC[best] = 1;
        for (int w : closeNb[best]) if (!covered[w]) {
            covered[w] = 1;
            coveredCnt++;
        }
    }

    // Prune redundant centers (while preserving domination)
    vector<int> domCount(N, 0);
    for (int u = 0; u < N; u++) if (inC[u]) {
        for (int w : closeNb[u]) domCount[w]++;
    }
    vector<int> centersInit;
    centersInit.reserve(N);
    for (int i = 0; i < N; i++) if (inC[i]) centersInit.push_back(i);
    // Sort centers by decreasing A to try to remove high A first
    vector<int> orderRemove = centersInit;
    sort(orderRemove.begin(), orderRemove.end(), [&](int lhs, int rhs){
        if (A[lhs] != A[rhs]) return A[lhs] > A[rhs];
        return lhs < rhs;
    });
    bool changed = true;
    while (changed) {
        changed = false;
        for (int u : orderRemove) if (inC[u]) {
            bool ok = true;
            for (int w : closeNb[u]) {
                if (domCount[w] - 1 <= 0) { ok = false; break; }
            }
            if (ok) {
                inC[u] = 0;
                changed = true;
                for (int w : closeNb[u]) domCount[w]--;
            }
        }
    }

    // Build centers list and mapping
    vector<int> centers;
    centers.reserve(N);
    for (int i = 0; i < N; i++) if (inC[i]) centers.push_back(i);
    int Cn = (int)centers.size();
    vector<int> idC(N, -1);
    for (int i = 0; i < Cn; i++) idC[centers[i]] = i;

    // For each non-center vertex, list adjacent centers (for assignment and weight splitting)
    vector<vector<int>> cNeighs(N);
    for (auto &e : edges) {
        int u = e.first, v = e.second;
        if (inC[u] && !inC[v]) cNeighs[v].push_back(idC[u]);
        if (inC[v] && !inC[u]) cNeighs[u].push_back(idC[v]);
    }
    // Remove duplicates in cNeighs
    for (int v = 0; v < N; v++) {
        auto &vec = cNeighs[v];
        if (!vec.empty()) {
            sort(vec.begin(), vec.end());
            vec.erase(unique(vec.begin(), vec.end()), vec.end());
        }
    }

    // Build centers graph
    vector<vector<int>> gC(Cn);
    for (auto &e : edges) {
        int u = e.first, v = e.second;
        int iu = idC[u], iv = idC[v];
        if (iu != -1 && iv != -1) {
            gC[iu].push_back(iv);
            gC[iv].push_back(iu);
        }
    }
    for (int i = 0; i < Cn; i++) {
        auto &vec = gC[i];
        sort(vec.begin(), vec.end());
        vec.erase(unique(vec.begin(), vec.end()), vec.end());
    }

    // Weight for centers: A[u] + sum of A[v]/deg for adjacent non-centers
    vector<double> wC(Cn, 0.0);
    for (int i = 0; i < Cn; i++) wC[i] = (double)A[centers[i]];
    for (int v = 0; v < N; v++) if (!inC[v]) {
        auto &vec = cNeighs[v];
        if (!vec.empty()) {
            double share = (double)A[v] / (double)vec.size();
            for (int cid : vec) wC[cid] += share;
        }
    }

    // BFS over centers with root ordering by ascending weight to encourage heavy nodes deeper
    int H2 = max(0, H - 1);
    vector<int> parentC(Cn, -1), depthC(Cn, -1);
    vector<char> visC(Cn, 0);
    vector<int> orderSeeds(Cn);
    iota(orderSeeds.begin(), orderSeeds.end(), 0);
    sort(orderSeeds.begin(), orderSeeds.end(), [&](int a, int b){
        if (wC[a] != wC[b]) return wC[a] < wC[b];
        if (A[centers[a]] != A[centers[b]]) return A[centers[a]] < A[centers[b]];
        return a < b;
    });
    for (int s : orderSeeds) {
        if (visC[s]) continue;
        // BFS from seed s with depth limit H2
        queue<int> q;
        visC[s] = 1;
        parentC[s] = -1;
        depthC[s] = 0;
        q.push(s);
        while (!q.empty()) {
            int u = q.front(); q.pop();
            if (depthC[u] >= H2) continue;
            for (int v : gC[u]) if (!visC[v]) {
                visC[v] = 1;
                parentC[v] = u;
                depthC[v] = depthC[u] + 1;
                q.push(v);
            }
        }
    }
    // Any remaining unvisited (shouldn't) -> assign as isolated roots
    for (int i = 0; i < Cn; i++) if (!visC[i]) {
        parentC[i] = -1;
        depthC[i] = 0;
    }

    // Assign parents for all vertices
    vector<int> parent(N, -1);
    // Centers -> parent centers
    for (int i = 0; i < Cn; i++) {
        int vtx = centers[i];
        if (parentC[i] == -1) parent[vtx] = -1;
        else parent[vtx] = centers[parentC[i]];
    }
    // Non-centers -> choose adjacent center with maximum depth
    for (int v = 0; v < N; v++) if (!inC[v]) {
        int bestCid = -1;
        int bestDepth = -1;
        auto &vec = cNeighs[v];
        if (!vec.empty()) {
            for (int cid : vec) {
                int d = depthC[cid];
                if (d > bestDepth) {
                    bestDepth = d;
                    bestCid = cid;
                } else if (d == bestDepth && bestCid != -1) {
                    // tie-break by lower A of center to keep heavy deeper elsewhere (minor)
                    if (A[centers[cid]] < A[centers[bestCid]]) bestCid = cid;
                }
            }
        }
        if (bestCid == -1) {
            // Fallback: pick any neighbor as parent, else be root (should not happen)
            if (!g[v].empty()) parent[v] = g[v][0];
            else parent[v] = -1;
        } else {
            parent[v] = centers[bestCid];
        }
    }

    // Output
    for (int i = 0; i < N; i++) {
        if (i) cout << ' ';
        cout << parent[i];
    }
    cout << '\n';

    return 0;
}