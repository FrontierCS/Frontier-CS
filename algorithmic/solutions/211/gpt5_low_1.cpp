#include <bits/stdc++.h>
using namespace std;

struct Device {
    int id;
    int x, y;
    char type; // 'R', 'S', 'C'
};

static inline long long sqdist(const Device& a, const Device& b) {
    long long dx = (long long)a.x - b.x;
    long long dy = (long long)a.y - b.y;
    return dx*dx + dy*dy;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N, K;
    if (!(cin >> N >> K)) {
        return 0;
    }
    vector<Device> robots; robots.reserve(N);
    vector<Device> relays; relays.reserve(K);
    for (int i = 0; i < N + K; ++i) {
        Device d;
        cin >> d.id >> d.x >> d.y >> d.type;
        if (d.type == 'C') relays.push_back(d);
        else robots.push_back(d);
    }
    // Safety: ensure correct counts
    if ((int)robots.size() != N || (int)relays.size() != K) {
        // Adjust if input order not strictly N robots then K relays
        // But per statement, there are N robots and K relay lines total; we already separated.
    }

    const long long INF = (long long)4e18;

    // Precompute Duc matrix: cost*10 for robot to relay edges (factor 1.0)
    vector<vector<long long>> Duc(N, vector<long long>(K, INF));
    for (int i = 0; i < N; ++i) {
        for (int c = 0; c < K; ++c) {
            long long D = sqdist(robots[i], relays[c]);
            Duc[i][c] = D * 10; // scale by 10
        }
    }

    auto w_rr = [&](int u, int v) -> long long {
        long long D = sqdist(robots[u], robots[v]);
        bool Su = (robots[u].type == 'S');
        bool Sv = (robots[v].type == 'S');
        long long factor = (Su || Sv) ? 8 : 10; // 0.8 or 1.0 scaled by 10
        return D * factor;
    };

    if (N == 0) {
        // No robots; trivial
        cout << "#\n#\n";
        return 0;
    }
    if (N == 1) {
        // Only one robot; no links needed
        cout << "#\n#\n";
        return 0;
    }

    // For each relay C, create ordering of robots by Dvc (ascending)
    vector<vector<int>> order(K);
    vector<int> ptr(K, 0);
    if (K > 0) {
        for (int c = 0; c < K; ++c) {
            order[c].resize(N);
            iota(order[c].begin(), order[c].end(), 0);
            sort(order[c].begin(), order[c].end(), [&](int a, int b){
                if (Duc[a][c] != Duc[b][c]) return Duc[a][c] < Duc[b][c];
                return a < b;
            });
        }
    }

    // Prim-like algorithm over robots with effective metric using relays
    vector<char> inTree(N, 0);
    int root = 0;
    inTree[root] = 1;
    int treeCount = 1;

    // direct connections maintenance
    vector<long long> bestDirect(N, INF);
    vector<int> parentDirect(N, -1);
    using PLI = pair<long long,int>;
    priority_queue<PLI, vector<PLI>, greater<PLI>> directPQ;
    for (int v = 0; v < N; ++v) if (v != root) {
        long long w = w_rr(root, v);
        bestDirect[v] = w;
        parentDirect[v] = root;
        directPQ.emplace(w, v);
    }

    // relay-assisted connections maintenance
    vector<long long> MC(K, INF); // best Duc among in-tree robots for each C
    vector<int> bestRobotForC(K, -1);
    vector<int> topV(K, -1);
    vector<long long> topD(K, INF);
    vector<long long> candidateC(K, INF);
    vector<int> verC(K, 0);

    auto refreshTop = [&](int c, const vector<char>& inTreeRef){
        while (ptr[c] < N && inTreeRef[ order[c][ptr[c]] ]) ptr[c]++;
        if (ptr[c] < N) {
            topV[c] = order[c][ptr[c]];
            topD[c] = Duc[topV[c]][c];
        } else {
            topV[c] = -1;
            topD[c] = INF;
        }
        if (MC[c] >= INF || topV[c] == -1) candidateC[c] = INF;
        else candidateC[c] = MC[c] + topD[c];
    };

    if (K > 0) {
        for (int c = 0; c < K; ++c) {
            MC[c] = Duc[root][c];
            bestRobotForC[c] = root;
            ptr[c] = 0;
            refreshTop(c, inTree);
        }
    }

    // Global heap over relays' candidates
    struct RCItem { long long val; int c; int ver; };
    struct RCComp {
        bool operator()(const RCItem& a, const RCItem& b) const {
            if (a.val != b.val) return a.val > b.val;
            if (a.c != b.c) return a.c > b.c;
            return a.ver > b.ver;
        }
    };
    priority_queue<RCItem, vector<RCItem>, RCComp> relPQ;
    if (K > 0) {
        for (int c = 0; c < K; ++c) {
            relPQ.push({candidateC[c], c, verC[c]});
        }
    }

    // Parent info for final reconstruction
    vector<int> parentRobot(N, -1);
    vector<int> parentRelay(N, -1); // -1 if direct

    while (treeCount < N) {
        // Get best direct
        long long bestDirVal = INF;
        int bestDirV = -1;
        while (!directPQ.empty()) {
            auto [val, v] = directPQ.top();
            if (inTree[v] || val != bestDirect[v]) {
                directPQ.pop();
                continue;
            }
            bestDirVal = val;
            bestDirV = v;
            break;
        }

        // Get best via relay
        long long bestViaVal = INF;
        int bestViaC = -1;
        int bestViaV = -1;
        int viaU = -1;
        if (K > 0) {
            while (!relPQ.empty()) {
                RCItem it = relPQ.top();
                if (it.ver != verC[it.c] || it.val != candidateC[it.c]) {
                    relPQ.pop();
                    continue;
                }
                // Ensure current topV consistent (should be by refresh after last step)
                bestViaVal = it.val;
                bestViaC = it.c;
                bestViaV = topV[it.c];
                viaU = bestRobotForC[it.c];
                break;
            }
        }

        bool chooseVia = false;
        if (bestViaVal < bestDirVal) chooseVia = true;
        else if (bestViaVal == bestDirVal && bestViaVal < INF) {
            // tie-breaker: prefer via or direct arbitrarily; choose via
            chooseVia = true;
        }

        int vstar = -1;
        int ustar = -1;
        int cstar = -1;

        if (chooseVia && bestViaVal < INF && bestViaV != -1 && !inTree[bestViaV]) {
            vstar = bestViaV;
            ustar = viaU;
            cstar = bestViaC;
            parentRobot[vstar] = ustar;
            parentRelay[vstar] = cstar;
        } else {
            if (bestDirVal >= INF || bestDirV == -1) {
                // Fallback: pick any remaining vertex (shouldn't happen)
                for (int v = 0; v < N; ++v) if (!inTree[v]) { bestDirV = v; break; }
            }
            vstar = bestDirV;
            ustar = parentDirect[vstar];
            cstar = -1;
            parentRobot[vstar] = ustar;
            parentRelay[vstar] = -1;
        }

        // Add vstar to tree
        inTree[vstar] = 1;
        treeCount++;

        // Update direct candidates
        for (int w = 0; w < N; ++w) if (!inTree[w]) {
            long long wv = w_rr(vstar, w);
            if (wv < bestDirect[w]) {
                bestDirect[w] = wv;
                parentDirect[w] = vstar;
                directPQ.emplace(wv, w);
            }
        }

        // Update relays: M_C and top candidates recompute
        if (K > 0) {
            for (int c = 0; c < K; ++c) {
                if (Duc[vstar][c] < MC[c]) {
                    MC[c] = Duc[vstar][c];
                    bestRobotForC[c] = vstar;
                }
                refreshTop(c, inTree);
                verC[c]++;
                relPQ.push({candidateC[c], c, verC[c]});
            }
        }
    }

    // Build edges set and selected relays set
    auto make_edge = [](int a, int b) -> pair<int,int> {
        if (a < b) return {a,b};
        else return {b,a};
    };

    // Map internal indices to IDs
    vector<int> robotID(N);
    for (int i = 0; i < N; ++i) robotID[i] = robots[i].id;
    vector<int> relayID(K);
    for (int i = 0; i < K; ++i) relayID[i] = relays[i].id;

    set<pair<int,int>> edgeSet; // store by actual IDs, ordered
    unordered_set<int> usedRelayIdx; usedRelayIdx.reserve(K*2+1);

    for (int v = 0; v < N; ++v) {
        if (v == root) continue;
        int u = parentRobot[v];
        int c = parentRelay[v];
        if (c == -1) {
            int a = robotID[u];
            int b = robotID[v];
            edgeSet.insert(make_edge(a,b));
        } else {
            int cid = relayID[c];
            int a = robotID[u];
            int b = robotID[v];
            edgeSet.insert(make_edge(a, cid));
            edgeSet.insert(make_edge(b, cid));
            usedRelayIdx.insert(c);
        }
    }

    // Output selected relays
    if (usedRelayIdx.empty()) {
        cout << "#\n";
    } else {
        vector<int> sel;
        sel.reserve(usedRelayIdx.size());
        for (int c : usedRelayIdx) sel.push_back(relayID[c]);
        sort(sel.begin(), sel.end());
        for (size_t i = 0; i < sel.size(); ++i) {
            if (i) cout << "#";
            cout << sel[i];
        }
        cout << "\n";
    }

    // Output edges
    if (edgeSet.empty()) {
        cout << "#\n";
    } else {
        bool first = true;
        for (auto &e : edgeSet) {
            if (!first) cout << "#";
            first = false;
            cout << e.first << "-" << e.second;
        }
        cout << "\n";
    }

    return 0;
}