#include <bits/stdc++.h>
using namespace std;

struct Edge {
    int from, to;
    string s;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N, M;
    if(!(cin >> N >> M)) return 0;
    int si, sj;
    cin >> si >> sj;
    vector<string> grid(N);
    for (int i = 0; i < N; ++i) cin >> grid[i];
    vector<string> t(M);
    for (int i = 0; i < M; ++i) cin >> t[i];

    // Build 2-gram graph for overlap=2
    const int K = 26;
    auto id2 = [&](char a, char b) { return (a - 'A') * K + (b - 'A'); };

    int V = K * K; // 676
    vector<Edge> edges;
    edges.reserve(M);
    vector<vector<int>> adj(V);
    vector<int> indeg(V, 0), outdeg(V, 0);

    for (int i = 0; i < M; ++i) {
        string s = t[i];
        int from = id2(s[0], s[1]);
        int to = id2(s[3], s[4]);
        Edge e{from, to, s};
        edges.push_back(e);
    }
    for (int i = 0; i < M; ++i) {
        adj[edges[i].from].push_back(i);
        outdeg[edges[i].from]++;
        indeg[edges[i].to]++;
    }

    vector<int> itptr(V, 0);
    vector<char> used(M, 0);

    auto extract_trail = [&](int start)->vector<int> {
        vector<int> trail_rev;
        vector<int> stV;
        vector<int> stE;
        stV.reserve(M+5);
        stE.reserve(M+5);
        stV.push_back(start);
        while (!stV.empty()) {
            int v = stV.back();
            int &it = itptr[v];
            while (it < (int)adj[v].size() && used[ adj[v][it] ]) it++;
            if (it == (int)adj[v].size()) {
                stV.pop_back();
                if (!stE.empty()) {
                    trail_rev.push_back(stE.back());
                    stE.pop_back();
                }
            } else {
                int eid = adj[v][it++];
                if (used[eid]) continue;
                used[eid] = 1;
                stV.push_back(edges[eid].to);
                stE.push_back(eid);
            }
        }
        reverse(trail_rev.begin(), trail_rev.end());
        return trail_rev;
    };

    vector<vector<int>> trails;
    // Start points based on out - in excess
    vector<int> starts;
    starts.reserve(M);
    for (int v = 0; v < V; ++v) {
        int extra = outdeg[v] - indeg[v];
        for (int k = 0; k < extra; ++k) starts.push_back(v);
    }
    // Extract trails from these starts
    for (int snode : starts) {
        // quick check if there is any unused outgoing from this node
        bool has = false;
        for (int x : adj[snode]) if (!used[x]) { has = true; break; }
        if (!has) continue;
        auto tr = extract_trail(snode);
        if (!tr.empty()) trails.push_back(move(tr));
    }
    // Cover remaining edges (for zero-sum components or leftover)
    for (;;) {
        int eid = -1;
        for (int i = 0; i < M; ++i) if (!used[i]) { eid = i; break; }
        if (eid == -1) break;
        auto tr = extract_trail(edges[eid].from);
        if (!tr.empty()) trails.push_back(move(tr));
    }

    // Merge trails if possible where end node of one equals start node of another
    int Tn = (int)trails.size();
    vector<int> startNode(Tn), endNode(Tn);
    for (int i = 0; i < Tn; ++i) {
        startNode[i] = edges[trails[i][0]].from;
        endNode[i] = edges[trails[i].back()].to;
    }
    vector<vector<int>> startMap(V);
    for (int i = 0; i < Tn; ++i) startMap[startNode[i]].push_back(i);

    vector<char> trailUsed(Tn, 0);
    vector<vector<int>> chains;
    chains.reserve(Tn);
    for (int i = 0; i < Tn; ++i) {
        if (trailUsed[i]) continue;
        vector<int> chain = trails[i];
        trailUsed[i] = 1;
        int curEnd = endNode[i];
        while (true) {
            auto &vec = startMap[curEnd];
            while (!vec.empty() && trailUsed[vec.back()]) vec.pop_back();
            if (vec.empty()) break;
            int j = vec.back();
            vec.pop_back();
            trailUsed[j] = 1;
            // append
            chain.insert(chain.end(), trails[j].begin(), trails[j].end());
            curEnd = endNode[j];
        }
        chains.push_back(move(chain));
    }

    // Build superstring S from chains with overlap of 2 within chains
    string S;
    S.reserve(3*M + 2*(int)chains.size() + 10);
    for (auto &chain : chains) {
        for (int idx = 0; idx < (int)chain.size(); ++idx) {
            const string &w = edges[chain[idx]].s;
            if (S.empty()) {
                S += w;
            } else {
                if (idx == 0) {
                    S += w;
                } else {
                    S += w.substr(2); // overlap 2 letters
                }
            }
        }
    }
    // Safety: if somehow chains is empty (shouldn't happen), fall back to concatenation
    if (S.empty()) {
        for (int i = 0; i < M; ++i) S += t[i];
    }

    // Prepare grid positions per letter
    struct Pos { int i, j; };
    vector<Pos> posList;
    posList.reserve(N*N);
    vector<vector<int>> byChar(26);
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            int id = (int)posList.size();
            posList.push_back({i,j});
            byChar[grid[i][j]-'A'].push_back(id);
        }
    }

    int L = (int)S.size();
    // DP arrays
    const long long INF = (1LL<<60);
    vector<long long> dpPrev, dpCur;
    vector<int> prevIDs, curIDs;
    vector<vector<int>> parentID(L);      // parent global posID
    vector<vector<int>> posIDsAtStep(L);  // posIDs for S[l]
    // step 0
    {
        char c = S[0];
        prevIDs = byChar[c-'A'];
        int sz = (int)prevIDs.size();
        dpPrev.assign(sz, INF);
        parentID[0].assign(sz, -1);
        posIDsAtStep[0] = prevIDs;
        for (int k = 0; k < sz; ++k) {
            int pid = prevIDs[k];
            long long cost = llabs(posList[pid].i - si) + llabs(posList[pid].j - sj) + 1;
            dpPrev[k] = cost;
        }
    }
    for (int l = 1; l < L; ++l) {
        char c = S[l];
        curIDs = byChar[c-'A'];
        int szc = (int)curIDs.size();
        int szp = (int)prevIDs.size();
        dpCur.assign(szc, INF);
        parentID[l].assign(szc, -1);
        posIDsAtStep[l] = curIDs;
        for (int k = 0; k < szc; ++k) {
            int pid = curIDs[k];
            auto &pc = posList[pid];
            long long best = INF;
            int bestParent = -1;
            for (int j = 0; j < szp; ++j) {
                int qid = prevIDs[j];
                auto &pp = posList[qid];
                long long cand = dpPrev[j] + llabs(pc.i - pp.i) + llabs(pc.j - pp.j) + 1;
                if (cand < best) {
                    best = cand;
                    bestParent = qid;
                }
            }
            dpCur[k] = best;
            parentID[l][k] = bestParent;
        }
        dpPrev.swap(dpCur);
        prevIDs.swap(curIDs);
    }
    // Backtrack
    int lastIndex = -1;
    long long bestCost = INF;
    for (int k = 0; k < (int)prevIDs.size(); ++k) {
        if (dpPrev[k] < bestCost) {
            bestCost = dpPrev[k];
            lastIndex = prevIDs[k];
        }
    }
    vector<int> chosenPosID(L);
    for (int l = L-1; l >= 0; --l) {
        chosenPosID[l] = lastIndex;
        if (l == 0) break;
        // find index of lastIndex in posIDsAtStep[l]
        int idx = -1;
        for (int k = 0; k < (int)posIDsAtStep[l].size(); ++k) {
            if (posIDsAtStep[l][k] == lastIndex) { idx = k; break; }
        }
        int parent = (idx == -1 ? -1 : parentID[l][idx]);
        lastIndex = parent;
    }

    // Output operations
    for (int l = 0; l < L; ++l) {
        auto &p = posList[chosenPosID[l]];
        cout << p.i << " " << p.j << "\n";
    }

    return 0;
}