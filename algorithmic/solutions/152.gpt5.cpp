#include <bits/stdc++.h>
using namespace std;

struct Order {
    int id;
    int ax, ay, cx, cy;
    int intra; // dist(a,c)
    long long singleCost; // dist(O,a) + dist(a,c) + dist(c,O)
};

static inline int manhattan(int x1, int y1, int x2, int y2) {
    return abs(x1 - x2) + abs(y1 - y2);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    const int OX = 400, OY = 400;
    vector<Order> orders;
    orders.reserve(1000);
    int a, b, c, d;
    int idx = 0;
    while (cin >> a >> b >> c >> d) {
        Order o;
        o.id = idx++;
        o.ax = a; o.ay = b; o.cx = c; o.cy = d;
        o.intra = manhattan(a, b, c, d);
        o.singleCost = (long long)manhattan(OX, OY, a, b) + o.intra + (long long)manhattan(c, d, OX, OY);
        orders.push_back(o);
    }
    int N = (int)orders.size();
    if (N == 0) {
        // Fallback: output trivial result
        cout << 0 << "\n";
        cout << 1 << " " << OX << " " << OY << "\n";
        return 0;
    }
    int K = min(50, N);

    // Sort by singleCost
    vector<int> allIdx(N);
    iota(allIdx.begin(), allIdx.end(), 0);
    sort(allIdx.begin(), allIdx.end(), [&](int i, int j){
        if (orders[i].singleCost != orders[j].singleCost) return orders[i].singleCost < orders[j].singleCost;
        return i < j;
    });

    int POOL = min(N, 300); // candidate pool size
    vector<int> poolIds(allIdx.begin(), allIdx.begin() + POOL);

    // Initial selection: first K from pool
    vector<int> selectedIds(poolIds.begin(), poolIds.begin() + K);
    vector<char> used(N, 0);
    for (int id : selectedIds) used[id] = 1;

    auto distStartToPick = [&](int id)->int {
        const auto &o = orders[id];
        return manhattan(OX, OY, o.ax, o.ay);
    };
    auto distDropToEnd = [&](int id)->int {
        const auto &o = orders[id];
        return manhattan(o.cx, o.cy, OX, OY);
    };
    auto distDropToPick = [&](int idFrom, int idTo)->int {
        const auto &a = orders[idFrom];
        const auto &b = orders[idTo];
        return manhattan(a.cx, a.cy, b.ax, b.ay);
    };

    // Build initial sequence by greedy nearest neighbor (on pickups)
    vector<int> seq; seq.reserve(K);
    vector<char> taken(K, 0);
    int curx = OX, cury = OY;
    vector<int> remain = selectedIds; // copy
    vector<char> chosen(N, 0);
    for (int id : remain) chosen[id] = 0; // not needed
    vector<char> mark(N, 0);
    for (int id : remain) mark[id] = 1;

    vector<char> usedLocal(N, 0);
    for (int iter = 0; iter < K; ++iter) {
        int bestId = -1;
        int bestDist = INT_MAX;
        for (int id : selectedIds) if (!usedLocal[id]) {
            int d0 = manhattan(curx, cury, orders[id].ax, orders[id].ay);
            if (d0 < bestDist) {
                bestDist = d0;
                bestId = id;
            }
        }
        if (bestId == -1) {
            // fallback (shouldn't happen)
            for (int id : selectedIds) if (!usedLocal[id]) { bestId = id; break; }
        }
        seq.push_back(bestId);
        usedLocal[bestId] = 1;
        curx = orders[bestId].cx; cury = orders[bestId].cy;
    }

    auto bridgingCost = [&](const vector<int>& p)->long long {
        if (p.empty()) return 0;
        long long cost = 0;
        cost += distStartToPick(p[0]);
        for (int i = 0; i + 1 < (int)p.size(); ++i) cost += distDropToPick(p[i], p[i+1]);
        cost += distDropToEnd(p.back());
        return cost;
    };

    // 2-opt optimization on sequence (only considering bridging part; intra part is constant)
    auto two_opt = [&](vector<int>& p){
        int k = (int)p.size();
        if (k <= 2) return;
        bool improved = true;
        int iter_guard = 0;
        while (improved && iter_guard < 1000) {
            ++iter_guard;
            improved = false;
            for (int i = 0; i < k; ++i) {
                for (int j = i + 1; j < k; ++j) {
                    // compute delta if reversing [i..j]
                    long long preBefore = (i == 0) ? distStartToPick(p[i]) : distDropToPick(p[i-1], p[i]);
                    long long postBefore = (j == k-1) ? distDropToEnd(p[j]) : distDropToPick(p[j], p[j+1]);
                    long long sumBefore = 0;
                    for (int t = i; t < j; ++t) sumBefore += distDropToPick(p[t], p[t+1]);

                    long long preAfter = (i == 0) ? distStartToPick(p[j]) : distDropToPick(p[i-1], p[j]);
                    long long postAfter = (j == k-1) ? distDropToEnd(p[i]) : distDropToPick(p[i], p[j+1]);
                    long long sumAfter = 0;
                    for (int t = i; t < j; ++t) sumAfter += distDropToPick(p[t+1], p[t]);

                    long long delta = (preAfter + sumAfter + postAfter) - (preBefore + sumBefore + postBefore);
                    if (delta < 0) {
                        reverse(p.begin() + i, p.begin() + j + 1);
                        improved = true;
                        goto next_iteration;
                    }
                }
            }
            next_iteration:;
        }
    };

    // Insertion optimization
    auto insertion_opt = [&](vector<int>& p){
        int k = (int)p.size();
        if (k <= 2) return;
        bool improved = true;
        int iter_guard = 0;
        while (improved && iter_guard < 1000) {
            ++iter_guard;
            improved = false;
            for (int i = 0; i < k; ++i) {
                for (int j = 0; j <= k; ++j) {
                    if (j == i || j == i + 1) continue;
                    int id = p[i];
                    // Removal delta
                    int prevId; // -1 for start
                    int nextId; // -2 for end
                    if (i == 0) prevId = -1; else prevId = p[i-1];
                    if (i == k-1) nextId = -2; else nextId = p[i+1];
                    long long preEdge = (prevId == -1) ? distStartToPick(p[i]) : distDropToPick(prevId, p[i]);
                    long long nextEdge = (nextId == -2) ? distDropToEnd(p[i]) : distDropToPick(p[i], nextId);
                    long long directEdge;
                    if (prevId == -1 && nextId == -2) {
                        directEdge = 0; // O -> O (no edge)
                    } else if (prevId == -1) {
                        directEdge = distStartToPick(nextId);
                    } else if (nextId == -2) {
                        directEdge = distDropToEnd(prevId);
                    } else {
                        directEdge = distDropToPick(prevId, nextId);
                    }
                    long long deltaRemove = directEdge - (preEdge + nextEdge);

                    // Insertion delta
                    int j2 = j;
                    if (j > i) j2 = j - 1;
                    int prev2Id = (j2 == 0) ? -1 : p[j2-1];
                    int next2Id = (j2 == k-1) ? -2 : p[j2];
                    long long oldEdge;
                    if (prev2Id == -1 && next2Id == -2) {
                        oldEdge = 0;
                    } else if (prev2Id == -1) {
                        oldEdge = distStartToPick(next2Id);
                    } else if (next2Id == -2) {
                        oldEdge = distDropToEnd(prev2Id);
                    } else {
                        oldEdge = distDropToPick(prev2Id, next2Id);
                    }
                    long long newEdges = ((prev2Id == -1) ? distStartToPick(id) : distDropToPick(prev2Id, id))
                                       + ((next2Id == -2) ? distDropToEnd(id) : distDropToPick(id, next2Id));
                    long long deltaInsert = newEdges - oldEdge;

                    long long delta = deltaRemove + deltaInsert;
                    if (delta < 0) {
                        int tmp = p[i];
                        p.erase(p.begin() + i);
                        if (j > i) j--;
                        p.insert(p.begin() + j, tmp);
                        k = (int)p.size();
                        improved = true;
                        goto next_iter2;
                    }
                }
            }
            next_iter2:;
        }
    };

    // Initial improvements
    two_opt(seq);
    insertion_opt(seq);
    two_opt(seq);

    // Replacement improvement from pool
    vector<char> chosenSet(N, 0);
    for (int id : seq) chosenSet[id] = 1;

    auto totalCost = [&](const vector<int>& p)->long long {
        if (p.empty()) return 0;
        long long cost = 0;
        // bridging + intra
        cost += distStartToPick(p[0]);
        for (int i = 0; i + 1 < (int)p.size(); ++i) cost += distDropToPick(p[i], p[i+1]);
        cost += distDropToEnd(p.back());
        for (int id : p) cost += orders[id].intra;
        return cost;
    };

    bool improvedRep = true;
    int repGuard = 0;
    while (improvedRep && repGuard < 5) { // limit replacement passes
        ++repGuard;
        improvedRep = false;
        for (int pos = 0; pos < K; ++pos) {
            int curId = seq[pos];
            int prevId = (pos == 0) ? -1 : seq[pos - 1];
            int nextId = (pos == K - 1) ? -2 : seq[pos + 1];
            long long preEdge = (prevId == -1) ? distStartToPick(curId) : distDropToPick(prevId, curId);
            long long nextEdge = (nextId == -2) ? distDropToEnd(curId) : distDropToPick(curId, nextId);
            long long baseCostCur = preEdge + nextEdge + orders[curId].intra;
            for (int cand : poolIds) {
                if (chosenSet[cand]) continue;
                long long preNew = (prevId == -1) ? distStartToPick(cand) : distDropToPick(prevId, cand);
                long long nextNew = (nextId == -2) ? distDropToEnd(cand) : distDropToPick(cand, nextId);
                long long baseCostNew = preNew + nextNew + orders[cand].intra;
                if (baseCostNew + 0 < baseCostCur) {
                    // Accept replacement
                    chosenSet[curId] = 0;
                    chosenSet[cand] = 1;
                    seq[pos] = cand;
                    improvedRep = true;
                    break;
                }
            }
        }
        if (improvedRep) {
            two_opt(seq);
            insertion_opt(seq);
        }
    }

    // Build route
    vector<pair<int,int>> path;
    path.reserve(1 + 2*K + 1);
    path.emplace_back(OX, OY);
    for (int id : seq) {
        path.emplace_back(orders[id].ax, orders[id].ay);
        path.emplace_back(orders[id].cx, orders[id].cy);
    }
    path.emplace_back(OX, OY);

    // Output
    cout << K;
    for (int id : seq) cout << " " << (id + 1);
    cout << "\n";
    cout << (int)path.size();
    for (auto &p : path) cout << " " << p.first << " " << p.second;
    cout << "\n";
    return 0;
}