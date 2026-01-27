#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    const int N = 30;
    const int TOTAL = N * (N + 1) / 2; // 465
    
    // Mapping between (x,y) and id
    vector<vector<int>> idOf(N);
    vector<int> X(TOTAL), Y(TOTAL);
    int id = 0;
    for (int x = 0; x < N; ++x) {
        idOf[x].resize(x + 1);
        for (int y = 0; y <= x; ++y) {
            idOf[x][y] = id;
            X[id] = x;
            Y[id] = y;
            id++;
        }
    }
    
    // Read values
    vector<int> val(TOTAL);
    for (int x = 0; x < N; ++x) {
        for (int y = 0; y <= x; ++y) {
            int b; 
            if (!(cin >> b)) b = 0;
            val[idOf[x][y]] = b;
        }
    }
    
    // Build vertical edges (parent->child)
    // Each edge is (upper_id, lower_id)
    vector<pair<int,int>> vertEdges;
    vector<vector<int>> vertEdgesByNode(TOTAL);
    for (int x = 0; x < N - 1; ++x) {
        for (int y = 0; y <= x; ++y) {
            int u = idOf[x][y];
            int v1 = idOf[x+1][y];
            int v2 = idOf[x+1][y+1];
            int idx1 = (int)vertEdges.size();
            vertEdges.emplace_back(u, v1);
            vertEdgesByNode[u].push_back(idx1);
            vertEdgesByNode[v1].push_back(idx1);
            int idx2 = (int)vertEdges.size();
            vertEdges.emplace_back(u, v2);
            vertEdgesByNode[u].push_back(idx2);
            vertEdgesByNode[v2].push_back(idx2);
        }
    }
    int V = (int)vertEdges.size(); // should be N*(N-1) = 870
    
    // Build adjacency edges for allowed swaps (6-direction neighbors)
    // We'll include vertical edges and horizontal edges (same tier neighbors)
    vector<pair<int,int>> swapEdges;
    swapEdges.reserve(3 * N * (N - 1) / 2);
    // vertical neighbors (already known)
    for (auto &e : vertEdges) {
        swapEdges.push_back(e); // (upper, lower)
    }
    // horizontal neighbors (same x, y and y+1)
    for (int x = 0; x < N; ++x) {
        for (int y = 0; y < x; ++y) {
            int a = idOf[x][y];
            int b = idOf[x][y+1];
            swapEdges.emplace_back(a, b);
        }
    }
    
    // Helper to compute current E
    auto computeE = [&]() {
        int E = 0;
        for (auto &e : vertEdges) {
            int u = e.first, v = e.second;
            if (val[u] > val[v]) ++E;
        }
        return E;
    };
    
    // Prepare for local delta evaluation
    vector<int> stamp(V, 0);
    int curStamp = 1;
    vector<int> affected;
    affected.reserve(16);
    
    auto getAffectedEdges = [&](int a, int b, vector<int>& out) {
        out.clear();
        int tag = ++curStamp;
        for (int idx : vertEdgesByNode[a]) {
            if (stamp[idx] != tag) {
                stamp[idx] = tag;
                out.push_back(idx);
            }
        }
        for (int idx : vertEdgesByNode[b]) {
            if (stamp[idx] != tag) {
                stamp[idx] = tag;
                out.push_back(idx);
            }
        }
    };
    
    auto deltaIfSwap = [&](int a, int b) {
        getAffectedEdges(a, b, affected);
        int before = 0, after = 0;
        int va = val[a], vb = val[b];
        for (int idx : affected) {
            int u = vertEdges[idx].first;
            int v = vertEdges[idx].second;
            int vu = val[u];
            int vv = val[v];
            if (vu > vv) ++before;
            // simulate swap: if u or v equals a/b, replace with swapped value
            int vu2 = (u == a ? vb : (u == b ? va : vu));
            int vv2 = (v == a ? vb : (v == b ? va : vv));
            if (vu2 > vv2) ++after;
        }
        return after - before;
    };
    
    // Local improvement loop
    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());
    vector<array<int,4>> moves;
    moves.reserve(10000);
    
    // Initial greedy improvements
    bool improved = true;
    int Ecur = computeE();
    while (improved) {
        improved = false;
        shuffle(swapEdges.begin(), swapEdges.end(), rng);
        for (auto &p : swapEdges) {
            if ((int)moves.size() >= 10000) break;
            int a = p.first, b = p.second;
            int d = deltaIfSwap(a, b);
            if (d < 0) {
                swap(val[a], val[b]);
                moves.push_back({X[a], Y[a], X[b], Y[b]});
                Ecur += d;
                improved = true;
            }
        }
        if ((int)moves.size() >= 10000) break;
    }
    
    // Output
    cout << moves.size() << '\n';
    for (auto &m : moves) {
        cout << m[0] << ' ' << m[1] << ' ' << m[2] << ' ' << m[3] << '\n';
    }
    return 0;
}