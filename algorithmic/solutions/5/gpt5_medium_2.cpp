#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m;
    if (!(cin >> n >> m)) return 0;
    // Read scoring parameters (unused)
    for (int i = 0; i < 10; ++i) {
        int tmp; cin >> tmp;
    }

    vector<int> U(m), V(m);
    vector<int> outdeg(n + 1, 0), indeg(n + 1, 0);
    for (int i = 0; i < m; ++i) {
        int u, v; cin >> u >> v;
        U[i] = u; V[i] = v;
        ++outdeg[u];
        ++indeg[v];
    }

    // Build CSR for outgoing edges
    vector<int> outStart(n + 2, 0), inStart(n + 2, 0);
    for (int i = 1; i <= n; ++i) outStart[i + 1] = outStart[i] + outdeg[i];
    for (int i = 1; i <= n; ++i) inStart[i + 1] = inStart[i] + indeg[i];
    vector<int> outAdj(m), inAdj(m);
    vector<int> curOut = outStart, curIn = inStart;
    for (int i = 0; i < m; ++i) {
        int u = U[i], v = V[i];
        outAdj[curOut[u]++] = v;
        inAdj[curIn[v]++] = u;
    }

    // Candidate starts
    vector<int> nodes(n);
    iota(nodes.begin(), nodes.end(), 1);

    auto cmp_out_minus_in = [&](int a, int b){
        int da = outdeg[a] - indeg[a];
        int db = outdeg[b] - indeg[b];
        if (da != db) return da > db;
        return outdeg[a] > outdeg[b];
    };
    auto cmp_in_minus_out = [&](int a, int b){
        int da = indeg[a] - outdeg[a];
        int db = indeg[b] - outdeg[b];
        if (da != db) return da > db;
        return indeg[a] > indeg[b];
    };
    auto cmp_out = [&](int a, int b){
        if (outdeg[a] != outdeg[b]) return outdeg[a] > outdeg[b];
        return indeg[a] > indeg[b];
    };
    auto cmp_in = [&](int a, int b){
        if (indeg[a] != indeg[b]) return indeg[a] > indeg[b];
        return outdeg[a] > outdeg[b];
    };

    vector<int> cand;
    cand.reserve(250);

    {
        vector<int> tmp = nodes;
        sort(tmp.begin(), tmp.end(), cmp_out_minus_in);
        int K = min<int>(50, tmp.size());
        for (int i = 0; i < K; ++i) cand.push_back(tmp[i]);
    }
    {
        vector<int> tmp = nodes;
        sort(tmp.begin(), tmp.end(), cmp_in_minus_out);
        int K = min<int>(50, tmp.size());
        for (int i = 0; i < K; ++i) cand.push_back(tmp[i]);
    }
    {
        vector<int> tmp = nodes;
        sort(tmp.begin(), tmp.end(), cmp_out);
        int K = min<int>(50, tmp.size());
        for (int i = 0; i < K; ++i) cand.push_back(tmp[i]);
    }
    {
        vector<int> tmp = nodes;
        sort(tmp.begin(), tmp.end(), cmp_in);
        int K = min<int>(50, tmp.size());
        for (int i = 0; i < K; ++i) cand.push_back(tmp[i]);
    }

    // Add random candidates
    uint64_t seed = chrono::high_resolution_clock::now().time_since_epoch().count();
    auto rng = [&]()->uint64_t {
        seed ^= seed << 7;
        seed ^= seed >> 9;
        return seed;
    };
    for (int i = 0; i < 50 && i < n; ++i) {
        int v = (rng() % n) + 1;
        cand.push_back(v);
    }

    // Deduplicate candidates and cap total
    sort(cand.begin(), cand.end());
    cand.erase(unique(cand.begin(), cand.end()), cand.end());
    if ((int)cand.size() > 200) cand.resize(200);

    vector<int> bestPath;
    bestPath.reserve(n);
    int bestLen = 0;

    vector<int> vis(n + 1, 0);
    int curMark = 1;

    auto build_from_start = [&](int s) {
        ++curMark;
        if (curMark == 0) { // overflow safety
            fill(vis.begin(), vis.end(), 0);
            curMark = 1;
        }
        vis[s] = curMark;
        vector<int> path; path.reserve(n);
        path.push_back(s);

        auto score = [&](int v)->int {
            // Heuristic score
            return outdeg[v]*2 + indeg[v];
        };

        // Extend back
        while (true) {
            int u = path.back();
            int bestv = -1;
            int bests = -1;
            int l = outStart[u], r = outStart[u+1];
            for (int i = l; i < r; ++i) {
                int v = outAdj[i];
                if (vis[v] == curMark) continue;
                int sc = score(v);
                if (sc > bests || (sc == bests && (rng() & 1))) {
                    bests = sc;
                    bestv = v;
                }
            }
            if (bestv == -1) break;
            vis[bestv] = curMark;
            path.push_back(bestv);
        }

        // Extend front
        vector<int> prefix; prefix.reserve(n);
        while (true) {
            int u = path.front();
            int bestv = -1;
            int bests = -1;
            int l = inStart[u], r = inStart[u+1];
            for (int i = l; i < r; ++i) {
                int v = inAdj[i];
                if (vis[v] == curMark) continue;
                int sc = score(v);
                if (sc > bests || (sc == bests && (rng() & 1))) {
                    bests = sc;
                    bestv = v;
                }
            }
            if (bestv == -1) break;
            vis[bestv] = curMark;
            prefix.push_back(bestv);
        }

        int len = (int)path.size() + (int)prefix.size();
        if (len > bestLen) {
            bestLen = len;
            bestPath.clear();
            bestPath.reserve(len);
            for (int i = (int)prefix.size() - 1; i >= 0; --i) bestPath.push_back(prefix[i]);
            for (int x : path) bestPath.push_back(x);
        }
    };

    if (cand.empty()) cand.push_back(1);
    for (int s : cand) {
        build_from_start(s);
        if (bestLen == n) break;
    }

    if (bestLen == 0) {
        // Fallback: at least a single vertex
        bestLen = 1;
        bestPath.clear();
        bestPath.push_back(1);
    }

    cout << bestLen << "\n";
    for (int i = 0; i < bestLen; ++i) {
        if (i) cout << ' ';
        cout << bestPath[i];
    }
    cout << "\n";
    return 0;
}