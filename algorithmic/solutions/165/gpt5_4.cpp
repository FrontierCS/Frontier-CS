#include <bits/stdc++.h>
using namespace std;

struct Pos { int i, j; };

static inline int manhattan(const Pos& a, const Pos& b) {
    return abs(a.i - b.i) + abs(a.j - b.j);
}

static inline int encode4(const string &s) {
    int id = 0;
    for (char c : s) id = id * 26 + (c - 'A');
    return id;
}

static inline string decode4(int id) {
    string s(4, 'A');
    for (int k = 3; k >= 0; --k) {
        s[k] = char('A' + (id % 26));
        id /= 26;
    }
    return s;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N, M;
    if (!(cin >> N >> M)) return 0;
    int si, sj;
    cin >> si >> sj;
    vector<string> grid(N);
    for (int i = 0; i < N; ++i) cin >> grid[i];
    vector<string> T(M);
    for (int k = 0; k < M; ++k) cin >> T[k];

    // Positions for each letter
    vector<vector<Pos>> posByChar(26);
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            char c = grid[i][j];
            posByChar[c - 'A'].push_back({i, j});
        }
    }

    // Build edges: start and end 4-grams
    vector<int> startId(M), endId(M);
    vector<char> lastChar(M);
    unordered_set<int> nodesSet;
    nodesSet.reserve(M * 2);
    for (int k = 0; k < M; ++k) {
        const string &t = T[k];
        string s4 = t.substr(0, 4);
        string e4 = t.substr(1, 4);
        startId[k] = encode4(s4);
        endId[k] = encode4(e4);
        lastChar[k] = t[4];
        nodesSet.insert(startId[k]);
        nodesSet.insert(endId[k]);
    }

    // Compress node ids
    vector<int> nodes;
    nodes.reserve(nodesSet.size());
    for (int x : nodesSet) nodes.push_back(x);
    sort(nodes.begin(), nodes.end());
    int K = (int)nodes.size();
    unordered_map<int,int> id2idx;
    id2idx.reserve(K * 2);
    for (int i = 0; i < K; ++i) id2idx[nodes[i]] = i;
    vector<string> nodeStr(K);
    for (int i = 0; i < K; ++i) nodeStr[i] = decode4(nodes[i]);

    vector<vector<int>> adj(K);
    vector<int> degOut(K, 0), degIn(K, 0);
    vector<int> sIdx(M), eIdx(M);
    for (int k = 0; k < M; ++k) {
        int u = id2idx[startId[k]];
        int v = id2idx[endId[k]];
        sIdx[k] = u;
        eIdx[k] = v;
        adj[u].push_back(k);
        degOut[u]++;
        degIn[v]++;
    }

    // Build superstring S using trails and bridging
    vector<vector<int>> adj_copy = adj; // mutate copy
    vector<int> degOutRem = degOut, degInRem = degIn;
    int edgesRemaining = M;

    auto choose_start_node = [&]() -> int {
        int best = -1;
        int bestScore = INT_MIN;
        int bestOut = -1;
        for (int i = 0; i < K; ++i) {
            if (!adj_copy[i].empty()) {
                int score = degOutRem[i] - degInRem[i];
                int outc = (int)adj_copy[i].size();
                if (score > bestScore || (score == bestScore && outc > bestOut)) {
                    bestScore = score;
                    bestOut = outc;
                    best = i;
                }
            }
        }
        if (best == -1) {
            // Should not happen if edgesRemaining > 0
            for (int i = 0; i < K; ++i) {
                if (!adj_copy[i].empty()) { best = i; break; }
            }
        }
        return best;
    };

    auto overlap4 = [&](const string &a, const string &b) -> int {
        // largest k in [0..4] such that suffix of a of length k equals prefix of b of length k
        for (int k = 4; k >= 0; --k) {
            bool ok = true;
            for (int i = 0; i < k; ++i) {
                if (a[4 - k + i] != b[i]) { ok = false; break; }
            }
            if (ok) return k;
        }
        return 0;
    };

    string S;
    int curr = -1;
    string currStr4;
    while (edgesRemaining > 0) {
        if (S.empty()) {
            curr = choose_start_node();
            currStr4 = nodeStr[curr];
            S += currStr4;
        }
        // Consume edges greedily from current node
        while (!adj_copy[curr].empty()) {
            int e = adj_copy[curr].back();
            adj_copy[curr].pop_back();
            S.push_back(lastChar[e]);
            int u = sIdx[e], v = eIdx[e];
            degOutRem[u]--; degInRem[v]--;
            edgesRemaining--;
            curr = v;
            currStr4 = nodeStr[curr]; // matches last 4 chars of S
        }
        if (edgesRemaining == 0) break;

        // Choose next node to jump to
        int best = -1;
        int bestPrefer = -1; // 1 if prefer (out>in), else 0
        int bestOverlap = -1;
        int bestOut = -1;
        for (int i = 0; i < K; ++i) {
            if (!adj_copy[i].empty()) {
                int prefer = (degOutRem[i] > degInRem[i]) ? 1 : 0;
                int ov = overlap4(currStr4, nodeStr[i]);
                int outc = (int)adj_copy[i].size();
                if (prefer > bestPrefer ||
                    (prefer == bestPrefer && ov > bestOverlap) ||
                    (prefer == bestPrefer && ov == bestOverlap && outc > bestOut)) {
                    bestPrefer = prefer;
                    bestOverlap = ov;
                    bestOut = outc;
                    best = i;
                }
            }
        }
        if (best == -1) break; // safety
        // Append bridge
        for (int k = bestOverlap; k < 4; ++k) S.push_back(nodeStr[best][k]);
        curr = best;
        currStr4 = nodeStr[curr];
    }

    // DP to choose positions minimizing movement
    int L = (int)S.size();
    if (L == 0) {
        // No moves - print nothing
        return 0;
    }

    vector<vector<int>> parents(L);
    vector<long long> dpPrev, dpCur;
    vector<Pos> prevPosList, curPosList;

    int c0 = S[0] - 'A';
    curPosList = posByChar[c0];
    int P = (int)curPosList.size();
    dpCur.assign(P, (long long)4e18);
    parents[0].assign(P, -1);
    for (int p = 0; p < P; ++p) {
        dpCur[p] = manhattan({si, sj}, curPosList[p]) + 1;
    }

    for (int i = 1; i < L; ++i) {
        dpPrev.swap(dpCur);
        prevPosList.swap(curPosList);
        int pc = S[i] - 'A';
        curPosList = posByChar[pc];
        int Q = (int)prevPosList.size();
        P = (int)curPosList.size();
        dpCur.assign(P, (long long)4e18);
        parents[i].assign(P, -1);
        for (int p = 0; p < P; ++p) {
            long long bestVal = (long long)4e18;
            int bestPar = -1;
            const Pos& curp = curPosList[p];
            for (int q = 0; q < Q; ++q) {
                long long val = dpPrev[q] + manhattan(prevPosList[q], curp) + 1;
                if (val < bestVal) {
                    bestVal = val;
                    bestPar = q;
                }
            }
            dpCur[p] = bestVal;
            parents[i][p] = bestPar;
        }
    }

    // Reconstruct path
    vector<int> chosenIdx(L);
    int lastCharIdx = S[L-1] - 'A';
    int lastP = (int)posByChar[lastCharIdx].size();
    long long bestFinal = (long long)4e18;
    int bestIdx = -1;
    for (int p = 0; p < lastP; ++p) {
        if (dpCur[p] < bestFinal) {
            bestFinal = dpCur[p];
            bestIdx = p;
        }
    }
    chosenIdx[L-1] = bestIdx;
    for (int i = L-1; i >= 1; --i) {
        chosenIdx[i-1] = parents[i][chosenIdx[i]];
    }

    // Output positions
    for (int i = 0; i < L; ++i) {
        int c = S[i] - 'A';
        const Pos& p = posByChar[c][chosenIdx[i]];
        cout << p.i << " " << p.j << "\n";
    }

    return 0;
}