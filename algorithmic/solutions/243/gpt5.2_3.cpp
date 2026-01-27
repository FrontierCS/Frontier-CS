#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int r, c;
    if (!(cin >> r >> c)) return 0;
    vector<string> g(r);
    for (int i = 0; i < r; i++) cin >> g[i];

    const int RC = r * c;
    const int M = RC * 4;
    const int V = 100;

    vector<int> rowOfCell(RC), colOfCell(RC);
    for (int i = 0; i < r; i++) for (int j = 0; j < c; j++) {
        int cell = i * c + j;
        rowOfCell[cell] = i;
        colOfCell[cell] = j;
    }

    vector<int> out(M, -1), nextL(M, -1), nextR(M, -1), nextS(M, -1), cellOf(M, -1);
    vector<int> statesAll;
    statesAll.reserve(M);

    const int dx[4] = {-1, 0, 1, 0};
    const int dy[4] = {0, 1, 0, -1};

    auto inside = [&](int x, int y) {
        return x >= 0 && x < r && y >= 0 && y < c;
    };

    for (int i = 0; i < r; i++) for (int j = 0; j < c; j++) {
        if (g[i][j] != '.') continue;
        int cell = i * c + j;
        for (int dir = 0; dir < 4; dir++) {
            int sid = cell * 4 + dir;
            cellOf[sid] = cell;

            int x = i + dx[dir], y = j + dy[dir];
            int k = 0;
            while (inside(x, y) && g[x][y] == '.') {
                k++;
                x += dx[dir];
                y += dy[dir];
            }
            out[sid] = k;

            nextL[sid] = cell * 4 + ((dir + 3) & 3);
            nextR[sid] = cell * 4 + ((dir + 1) & 3);

            int nx = i + dx[dir], ny = j + dy[dir];
            if (inside(nx, ny) && g[nx][ny] == '.') {
                int ncell = nx * c + ny;
                nextS[sid] = ncell * 4 + dir;
            } else {
                nextS[sid] = -1;
            }

            statesAll.push_back(sid);
        }
    }

    // Compute bisimulation-style equivalence classes w.r.t. outputs and allowed actions.
    vector<int> cls(M, -1), newCls(M, -1);
    for (int s : statesAll) cls[s] = out[s]; // initial partition by output

    constexpr int B = 17;
    constexpr int SH_L = 7;
    constexpr int SH_R = 7 + B;
    constexpr int SH_S = 7 + 2 * B;

    while (true) {
        unordered_map<uint64_t, int> mp;
        mp.reserve(statesAll.size() * 2);

        int nid = 0;
        bool changed = false;
        for (int s : statesAll) {
            int clL = cls[nextL[s]];
            int clR = cls[nextR[s]];
            int clS = (out[s] > 0 ? cls[nextS[s]] : -1);

            uint64_t key = (uint64_t)out[s];
            key |= (uint64_t)(clL + 1) << SH_L;
            key |= (uint64_t)(clR + 1) << SH_R;
            key |= (uint64_t)(clS + 1) << SH_S;

            auto it = mp.find(key);
            if (it == mp.end()) {
                mp.emplace(key, nid);
                newCls[s] = nid;
                nid++;
            } else {
                newCls[s] = it->second;
            }
        }

        for (int s : statesAll) {
            if (newCls[s] != cls[s]) {
                changed = true;
                break;
            }
        }
        if (!changed) break;
        for (int s : statesAll) cls[s] = newCls[s];
    }

    int classCount = 0;
    for (int s : statesAll) classCount = max(classCount, cls[s] + 1);

    vector<int> firstCell(classCount, -1);
    vector<char> multiCell(classCount, 0);
    for (int s : statesAll) {
        int cid = cls[s];
        int cell = cellOf[s];
        if (firstCell[cid] == -1) firstCell[cid] = cell;
        else if (firstCell[cid] != cell) multiCell[cid] = 1;
    }

    vector<int> belief = statesAll; // unique set of possible states

    vector<int> stateMark(M, 0);
    int stateStamp = 1;

    vector<int> pairMark(V * RC, 0);
    int pairStamp = 1;

    auto trans = [&](int s, int a) -> int {
        if (a == 0) return nextL[s];
        if (a == 1) return nextR[s];
        return nextS[s];
    };

    int d;
    while (cin >> d) {
        if (d == -1) return 0;

        // Filter by current observation
        {
            vector<int> filtered;
            filtered.reserve(belief.size());
            for (int s : belief) if (out[s] == d) filtered.push_back(s);
            belief.swap(filtered);
        }

        if (belief.empty()) {
            cout << "no\n" << flush;
            return 0;
        }

        // Check if position is known
        int cell0 = cellOf[belief[0]];
        bool sameCell = true;
        for (int s : belief) {
            if (cellOf[s] != cell0) { sameCell = false; break; }
        }
        if (sameCell) {
            cout << "yes " << (rowOfCell[cell0] + 1) << " " << (colOfCell[cell0] + 1) << "\n" << flush;
            return 0;
        }

        // Provably impossible: all remaining states are in same indistinguishability class spanning >1 cell
        int cls0 = cls[belief[0]];
        bool sameCls = true;
        for (int s : belief) {
            if (cls[s] != cls0) { sameCls = false; break; }
        }
        if (sameCls && multiCell[cls0]) {
            cout << "no\n" << flush;
            return 0;
        }

        vector<int> actions;
        if (d > 0) actions = {2, 0, 1}; // prefer step on ties
        else actions = {0, 1};

        tuple<int,int,long long,long long,int,int> best = {INT_MAX, INT_MAX, LLONG_MAX, LLONG_MAX, INT_MAX, INT_MAX};
        int bestAct = actions[0];

        for (int a : actions) {
            if (++pairStamp == INT_MAX) {
                fill(pairMark.begin(), pairMark.end(), 0);
                pairStamp = 1;
            }

            array<int, V> cntS{};
            array<int, V> cntC{};
            int kinds = 0;

            for (int s : belief) {
                int ns = trans(s, a);
                int v = out[ns];
                cntS[v]++;

                int idx = v * RC + cellOf[ns];
                if (pairMark[idx] != pairStamp) {
                    pairMark[idx] = pairStamp;
                    cntC[v]++;
                }
            }

            int worstC = 0, worstS = 0;
            long long sumC2 = 0, sumS2 = 0;
            for (int v = 0; v < V; v++) {
                if (cntS[v] == 0) continue;
                kinds++;
                worstC = max(worstC, cntC[v]);
                worstS = max(worstS, cntS[v]);
                sumC2 += 1LL * cntC[v] * cntC[v];
                sumS2 += 1LL * cntS[v] * cntS[v];
            }

            int pref = (a == 2 ? 0 : 1);
            auto cand = make_tuple(worstC, worstS, sumC2, sumS2, -kinds, pref);
            if (cand < best) {
                best = cand;
                bestAct = a;
            }
        }

        if (bestAct == 0) cout << "left\n" << flush;
        else if (bestAct == 1) cout << "right\n" << flush;
        else cout << "step\n" << flush;

        // Apply action to belief (deduplicate)
        if (++stateStamp == INT_MAX) {
            fill(stateMark.begin(), stateMark.end(), 0);
            stateStamp = 1;
        }
        vector<int> nb;
        nb.reserve(belief.size());
        for (int s : belief) {
            int ns = trans(s, bestAct);
            if (stateMark[ns] != stateStamp) {
                stateMark[ns] = stateStamp;
                nb.push_back(ns);
            }
        }
        belief.swap(nb);
    }

    return 0;
}