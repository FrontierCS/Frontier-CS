#include <bits/stdc++.h>
using namespace std;

enum Action { ACT_LEFT = 0, ACT_RIGHT = 1, ACT_STEP = 2 };

struct Metrics {
    int worstPos1;
    int worstPos2;
    int worstStates1;
    int priority;
    Action act;
};

static inline bool betterMetrics(const Metrics& a, const Metrics& b) {
    if (a.worstPos1 != b.worstPos1) return a.worstPos1 < b.worstPos1;
    if (a.worstPos2 != b.worstPos2) return a.worstPos2 < b.worstPos2;
    if (a.worstStates1 != b.worstStates1) return a.worstStates1 < b.worstStates1;
    return a.priority < b.priority;
}

struct Key {
    int o, l, r, s;
    bool operator<(const Key& other) const {
        if (o != other.o) return o < other.o;
        if (l != other.l) return l < other.l;
        if (r != other.r) return r < other.r;
        return s < other.s;
    }
    bool operator==(const Key& other) const {
        return o == other.o && l == other.l && r == other.r && s == other.s;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int R, C;
    cin >> R >> C;
    vector<string> g(R);
    for (int i = 0; i < R; i++) cin >> g[i];

    vector<int> cellId(R * C, -1);
    vector<int> cellR, cellC;
    cellR.reserve(R * C);
    cellC.reserve(R * C);

    int M = 0;
    for (int i = 0; i < R; i++) {
        for (int j = 0; j < C; j++) {
            if (g[i][j] == '.') {
                cellId[i * C + j] = M++;
                cellR.push_back(i + 1);
                cellC.push_back(j + 1);
            }
        }
    }

    int N = M * 4;
    vector<int> obs(N, 0);
    vector<int> nxtL(N), nxtR(N), nxtS(N, -1);

    auto inside = [&](int x, int y) -> bool { return x >= 0 && x < R && y >= 0 && y < C; };
    const int dr[4] = {-1, 0, 1, 0};
    const int dc[4] = {0, 1, 0, -1};

    // Precompute obs and transitions
    for (int i = 0; i < R; i++) {
        for (int j = 0; j < C; j++) {
            int cid = cellId[i * C + j];
            if (cid < 0) continue;

            for (int d = 0; d < 4; d++) {
                int sid = cid * 4 + d;

                int cnt = 0;
                int x = i + dr[d], y = j + dc[d];
                while (inside(x, y) && g[x][y] == '.') {
                    cnt++;
                    x += dr[d];
                    y += dc[d];
                }
                obs[sid] = cnt;

                nxtL[sid] = cid * 4 + ((d + 3) & 3);
                nxtR[sid] = cid * 4 + ((d + 1) & 3);

                if (cnt > 0) {
                    int ni = i + dr[d], nj = j + dc[d];
                    int ncid = cellId[ni * C + nj];
                    nxtS[sid] = ncid * 4 + d;
                } else {
                    nxtS[sid] = -1;
                }
            }
        }
    }

    // Check global impossibility via partition refinement (coarsest congruence)
    vector<int> cls(N), newCls(N);
    for (int s = 0; s < N; s++) cls[s] = obs[s];

    vector<Key> keys(N);
    vector<int> order(N);
    iota(order.begin(), order.end(), 0);

    while (true) {
        for (int s = 0; s < N; s++) {
            int sl = nxtL[s], sr = nxtR[s], ss = nxtS[s];
            keys[s] = Key{obs[s], cls[sl], cls[sr], (ss < 0 ? -1 : cls[ss])};
        }

        sort(order.begin(), order.end(), [&](int a, int b) {
            const Key& ka = keys[a];
            const Key& kb = keys[b];
            if (ka.o != kb.o) return ka.o < kb.o;
            if (ka.l != kb.l) return ka.l < kb.l;
            if (ka.r != kb.r) return ka.r < kb.r;
            return ka.s < kb.s;
        });

        int cid = 0;
        newCls[order[0]] = 0;
        for (int i = 1; i < N; i++) {
            if (!(keys[order[i]] == keys[order[i - 1]])) cid++;
            newCls[order[i]] = cid;
        }

        if (newCls == cls) break;
        cls.swap(newCls);
    }

    int maxCls = 0;
    for (int s = 0; s < N; s++) maxCls = max(maxCls, cls[s]);
    int numCls = maxCls + 1;

    bool impossible = false;
    vector<int> repCell(numCls, -1);
    for (int s = 0; s < N; s++) {
        int k = cls[s];
        int cidx = s >> 2;
        if (repCell[k] == -1) repCell[k] = cidx;
        else if (repCell[k] != cidx) {
            impossible = true;
            break;
        }
    }

    auto send = [&](const string& cmd) {
        cout << cmd << "\n" << flush;
    };

    // Prepare initial belief: all states
    vector<int> belief;
    belief.reserve(N);
    for (int s = 0; s < N; s++) belief.push_back(s);
    vector<int> tmp;
    tmp.reserve(N);

    vector<long long> markCell(M, LLONG_MIN);
    long long globalTag = 1;

    auto distinctCellsInSet = [&](const vector<int>& S) -> int {
        long long tag = (globalTag++ << 7);
        int cnt = 0;
        for (int s : S) {
            int cidx = s >> 2;
            if (markCell[cidx] != tag) {
                markCell[cidx] = tag;
                cnt++;
            }
        }
        return cnt;
    };

    auto bestWorstPos1 = [&](const vector<int>& S, int obsVal) -> int {
        int best = INT_MAX;
        for (int b = 0; b < 3; b++) {
            Action act = (Action)b;
            if (act == ACT_STEP && obsVal == 0) continue;

            int distinct[100] = {0};
            int cnts[100] = {0};
            long long base = (globalTag++ << 7);

            for (int s : S) {
                int t;
                if (act == ACT_LEFT) t = nxtL[s];
                else if (act == ACT_RIGHT) t = nxtR[s];
                else t = nxtS[s];

                int o2 = obs[t];
                cnts[o2]++;
                int cidx = t >> 2;
                long long tag = base + o2;
                if (markCell[cidx] != tag) {
                    markCell[cidx] = tag;
                    distinct[o2]++;
                }
            }

            int worst = 0;
            for (int o2 = 0; o2 < 100; o2++) if (cnts[o2] > 0) worst = max(worst, distinct[o2]);
            best = min(best, worst);
            if (best == 1) break;
        }
        return best;
    };

    array<vector<int>, 100> groups;
    for (auto& v : groups) v.reserve(256);

    auto evalAction = [&](Action act, const vector<int>& B, int curObs) -> Metrics {
        for (auto& v : groups) v.clear();

        int distinct[100] = {0};
        int cnts[100] = {0};
        long long base = (globalTag++ << 7);

        for (int s : B) {
            int t;
            if (act == ACT_LEFT) t = nxtL[s];
            else if (act == ACT_RIGHT) t = nxtR[s];
            else t = nxtS[s];

            int o = obs[t];
            groups[o].push_back(t);
            cnts[o]++;

            int cidx = t >> 2;
            long long tag = base + o;
            if (markCell[cidx] != tag) {
                markCell[cidx] = tag;
                distinct[o]++;
            }
        }

        int worstPos1 = 0, worstStates1 = 0;
        for (int o = 0; o < 100; o++) if (cnts[o] > 0) {
            worstPos1 = max(worstPos1, distinct[o]);
            worstStates1 = max(worstStates1, cnts[o]);
        }

        int worstPos2 = 0;
        for (int o = 0; o < 100; o++) {
            if (cnts[o] == 0) continue;
            int branch;
            if (distinct[o] == 1) branch = 1;
            else branch = bestWorstPos1(groups[o], o);
            worstPos2 = max(worstPos2, branch);
        }

        int pri;
        if (act == ACT_STEP) pri = 0;
        else if (act == ACT_RIGHT) pri = 1;
        else pri = 2;

        return Metrics{worstPos1, worstPos2, worstStates1, pri, act};
    };

    int d;
    int stagnation = 0;
    int prevDistinct = -1;
    const int STAG_LIMIT = 10;

    while (cin >> d) {
        if (d == -1) return 0;

        if (impossible) {
            send("no");
            return 0;
        }

        // Filter by current observation
        tmp.clear();
        tmp.reserve(belief.size());
        for (int s : belief) if (obs[s] == d) tmp.push_back(s);
        belief.swap(tmp);

        // Determine if position is unique
        int curDistinct = distinctCellsInSet(belief);
        if (curDistinct == 1) {
            int cell = belief[0] >> 2;
            send("yes " + to_string(cellR[cell]) + " " + to_string(cellC[cell]));
            return 0;
        }

        if (prevDistinct == -1 || curDistinct < prevDistinct) stagnation = 0;
        else stagnation++;
        prevDistinct = curDistinct;

        vector<Action> acts;
        acts.push_back(ACT_LEFT);
        acts.push_back(ACT_RIGHT);
        if (d > 0) acts.push_back(ACT_STEP);

        Metrics best;
        bool hasBest = false;

        // If stagnating, force some movement/variation
        if (stagnation >= STAG_LIMIT) {
            Action forced = (d > 0 ? ACT_STEP : ACT_RIGHT);
            if (forced == ACT_LEFT) send("left");
            else if (forced == ACT_RIGHT) send("right");
            else send("step");

            tmp.clear();
            tmp.reserve(belief.size());
            for (int s : belief) {
                int t = (forced == ACT_LEFT ? nxtL[s] : (forced == ACT_RIGHT ? nxtR[s] : nxtS[s]));
                tmp.push_back(t);
            }
            belief.swap(tmp);
            stagnation = 0;
            continue;
        }

        for (Action act : acts) {
            Metrics m = evalAction(act, belief, d);
            if (!hasBest || betterMetrics(m, best)) {
                best = m;
                hasBest = true;
            }
        }

        if (best.act == ACT_LEFT) send("left");
        else if (best.act == ACT_RIGHT) send("right");
        else send("step");

        tmp.clear();
        tmp.reserve(belief.size());
        for (int s : belief) {
            int t = (best.act == ACT_LEFT ? nxtL[s] : (best.act == ACT_RIGHT ? nxtR[s] : nxtS[s]));
            tmp.push_back(t);
        }
        belief.swap(tmp);
    }

    return 0;
}