#include <bits/stdc++.h>
using namespace std;

static inline uint64_t splitmix64(uint64_t x) {
    x += 0x9e3779b97f4a7c15ULL;
    x = (x ^ (x >> 30)) * 0xbf58476d1ce4e5b9ULL;
    x = (x ^ (x >> 27)) * 0x94d049bb133111ebULL;
    return x ^ (x >> 31);
}

struct EvalRes {
    int worst2;
    int worst1;
    int pref;
    int action;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int r, c;
    if (!(cin >> r >> c)) return 0;
    vector<string> g(r);
    for (int i = 0; i < r; i++) cin >> g[i];

    vector<vector<int>> cellId(r, vector<int>(c, -1));
    vector<pair<int,int>> cellCoord;
    cellCoord.reserve(r * c);
    for (int i = 0; i < r; i++) {
        for (int j = 0; j < c; j++) {
            if (g[i][j] == '.') {
                cellId[i][j] = (int)cellCoord.size();
                cellCoord.push_back({i, j});
            }
        }
    }
    int openCnt = (int)cellCoord.size();
    if (openCnt == 0) return 0;

    vector<vector<char>> open(r, vector<char>(c, 0));
    for (int i = 0; i < r; i++)
        for (int j = 0; j < c; j++)
            open[i][j] = (g[i][j] == '.');

    vector<vector<int>> east(r, vector<int>(c, 0));
    vector<vector<int>> west(r, vector<int>(c, 0));
    vector<vector<int>> north(r, vector<int>(c, 0));
    vector<vector<int>> south(r, vector<int>(c, 0));

    for (int i = 0; i < r; i++) {
        for (int j = c - 1; j >= 0; j--) {
            if (!open[i][j]) continue;
            if (j == c - 1 || !open[i][j + 1]) east[i][j] = 0;
            else east[i][j] = 1 + east[i][j + 1];
        }
        for (int j = 0; j < c; j++) {
            if (!open[i][j]) continue;
            if (j == 0 || !open[i][j - 1]) west[i][j] = 0;
            else west[i][j] = 1 + west[i][j - 1];
        }
    }
    for (int j = 0; j < c; j++) {
        for (int i = 0; i < r; i++) {
            if (!open[i][j]) continue;
            if (i == 0 || !open[i - 1][j]) north[i][j] = 0;
            else north[i][j] = 1 + north[i - 1][j];
        }
        for (int i = r - 1; i >= 0; i--) {
            if (!open[i][j]) continue;
            if (i == r - 1 || !open[i + 1][j]) south[i][j] = 0;
            else south[i][j] = 1 + south[i + 1][j];
        }
    }

    static const int dx[4] = {-1, 0, 1, 0};
    static const int dy[4] = {0, 1, 0, -1};

    int N = openCnt * 4;
    int crash = N;
    int M = N + 1;

    vector<int> stateCell(N, -1);
    vector<uint16_t> outEnc(M, 0); // 0..99 for normal, 100 for crash
    vector<array<int,3>> tr(M);
    for (int i = 0; i < M; i++) tr[i] = {crash, crash, crash};

    for (int cid = 0; cid < openCnt; cid++) {
        auto [i, j] = cellCoord[cid];
        for (int dir = 0; dir < 4; dir++) {
            int sid = cid * 4 + dir;
            stateCell[sid] = cid;
            int dist = 0;
            if (dir == 0) dist = north[i][j];
            else if (dir == 1) dist = east[i][j];
            else if (dir == 2) dist = south[i][j];
            else dist = west[i][j];
            outEnc[sid] = (uint16_t)dist;

            int leftDir = (dir + 3) & 3;
            int rightDir = (dir + 1) & 3;
            tr[sid][0] = cid * 4 + leftDir;
            tr[sid][1] = cid * 4 + rightDir;

            int ni = i + dx[dir], nj = j + dy[dir];
            int nextCell = (ni >= 0 && ni < r && nj >= 0 && nj < c) ? cellId[ni][nj] : -1;
            if (dist > 0) {
                if (nextCell < 0) tr[sid][2] = crash;
                else tr[sid][2] = nextCell * 4 + dir;
            } else {
                tr[sid][2] = crash;
            }
        }
    }
    outEnc[crash] = 100;
    tr[crash] = {crash, crash, crash};

    // Moore machine minimization by iterative refinement
    vector<int> cls(M);
    for (int i = 0; i < M; i++) cls[i] = (int)outEnc[i];

    while (true) {
        unordered_map<uint64_t, int> mp;
        mp.reserve((size_t)M * 2);
        mp.max_load_factor(0.7f);

        vector<int> ncls(M);
        int nextId = 0;

        for (int i = 0; i < M; i++) {
            uint64_t key = (uint64_t)outEnc[i];
            key = (key << 17) | (uint64_t)cls[tr[i][0]];
            key = (key << 17) | (uint64_t)cls[tr[i][1]];
            key = (key << 17) | (uint64_t)cls[tr[i][2]];
            auto it = mp.find(key);
            if (it == mp.end()) {
                mp.emplace(key, nextId);
                ncls[i] = nextId;
                nextId++;
            } else {
                ncls[i] = it->second;
            }
        }
        if (ncls == cls) break;
        cls.swap(ncls);
    }

    int K = 0;
    for (int x : cls) K = max(K, x + 1);

    vector<int> rep(K, -1);
    for (int i = 0; i < M; i++) if (rep[cls[i]] == -1) rep[cls[i]] = i;

    vector<int> classOut(K, 0);
    vector<array<int,3>> classTr(K);
    for (int k = 0; k < K; k++) {
        int s = rep[k];
        classOut[k] = (int)outEnc[s];
        classTr[k][0] = cls[tr[s][0]];
        classTr[k][1] = cls[tr[s][1]];
        classTr[k][2] = cls[tr[s][2]];
    }

    vector<int> classCell(K, -1);
    bool possible = true;
    for (int sid = 0; sid < N; sid++) {
        int k = cls[sid];
        int cid = stateCell[sid];
        if (classCell[k] == -1) classCell[k] = cid;
        else if (classCell[k] != cid) { possible = false; break; }
    }

    int d;
    if (!(cin >> d)) return 0;
    if (d == -1) return 0;

    if (!possible) {
        cout << "no" << '\n' << flush;
        return 0;
    }

    vector<char> classHas(K, 0);
    for (int sid = 0; sid < N; sid++) classHas[cls[sid]] = 1;

    vector<int> belief;
    belief.reserve(K);
    for (int k = 0; k < K; k++) {
        if (classHas[k] && classOut[k] >= 0 && classOut[k] <= 99) belief.push_back(k);
    }

    vector<int> markClass(K, 0);
    int stampClass = 1;
    vector<int> seenCell(openCnt, 0);
    int stampCell = 1;

    auto cellCount = [&](const vector<int>& B) -> int {
        stampCell++;
        int cnt = 0;
        for (int k : B) {
            int cid = classCell[k];
            if (cid < 0) continue;
            if (seenCell[cid] != stampCell) {
                seenCell[cid] = stampCell;
                cnt++;
            }
        }
        return cnt;
    };

    auto isUniqueCell = [&](const vector<int>& B) -> bool {
        if (B.empty()) return false;
        int cid = classCell[B[0]];
        for (int k : B) if (classCell[k] != cid) return false;
        return true;
    };

    vector<vector<int>> groups1(101), groups2(101);
    vector<int> usedObs1, usedObs2;
    usedObs1.reserve(101);
    usedObs2.reserve(101);

    auto partitionByObs = [&](const vector<int>& B, int action,
                              vector<vector<int>>& groups, vector<int>& usedObs) {
        usedObs.clear();
        stampClass++;
        for (int k : B) {
            int k1 = classTr[k][action];
            if (markClass[k1] == stampClass) continue;
            markClass[k1] = stampClass;
            int o = classOut[k1];
            if (o < 0) o = 100;
            if (o > 100) o = 100;
            if (groups[o].empty()) usedObs.push_back(o);
            groups[o].push_back(k1);
        }
    };

    auto clearGroups = [&](vector<vector<int>>& groups, const vector<int>& usedObs) {
        for (int o : usedObs) groups[o].clear();
    };

    auto bestSecondStep = [&](const vector<int>& B1, int obs1) -> int {
        int best = INT_MAX;
        int actions[3] = {0, 1, 2}; // left, right, step
        int actionCnt = (obs1 > 0 && obs1 <= 99) ? 3 : 2;
        for (int ai = 0; ai < actionCnt; ai++) {
            int a2 = actions[ai];
            partitionByObs(B1, a2, groups2, usedObs2);
            int worst = 0;
            for (int o2 : usedObs2) {
                int cc2 = cellCount(groups2[o2]);
                worst = max(worst, cc2);
            }
            clearGroups(groups2, usedObs2);
            best = min(best, worst);
        }
        return best;
    };

    auto evalAction = [&](const vector<int>& B, int action) -> EvalRes {
        partitionByObs(B, action, groups1, usedObs1);
        int worst1 = 0, worst2 = 0;
        for (int o1 : usedObs1) {
            auto &B1 = groups1[o1];
            int cc1 = cellCount(B1);
            worst1 = max(worst1, cc1);
            int g2 = (cc1 == 1) ? 0 : bestSecondStep(B1, o1);
            worst2 = max(worst2, g2);
        }
        clearGroups(groups1, usedObs1);

        int pref = 0;
        // prefer step, then right, then left
        if (action == 2) pref = 0;
        else if (action == 1) pref = 1;
        else pref = 2;

        return {worst2, worst1, pref, action};
    };

    auto applyAction = [&](const vector<int>& B, int action) -> vector<int> {
        vector<int> nb;
        nb.reserve(B.size());
        stampClass++;
        for (int k : B) {
            int k1 = classTr[k][action];
            if (classOut[k1] == 100) continue; // avoid crash class
            if (markClass[k1] == stampClass) continue;
            markClass[k1] = stampClass;
            nb.push_back(k1);
        }
        return nb;
    };

    auto filterByObs = [&](vector<int>& B, int obs) {
        vector<int> nb;
        nb.reserve(B.size());
        for (int k : B) if (classOut[k] == obs) nb.push_back(k);
        B.swap(nb);
    };

    unordered_map<uint64_t, int> seenBeliefCount;
    seenBeliefCount.reserve(1 << 15);
    seenBeliefCount.max_load_factor(0.7f);

    auto hashBelief = [&](const vector<int>& B, int obs) -> uint64_t {
        uint64_t h = splitmix64((uint64_t)B.size()) ^ splitmix64((uint64_t)obs + 1234567ULL);
        for (int k : B) h ^= splitmix64((uint64_t)k + 0x9e3779b97f4a7c15ULL);
        return h;
    };

    while (true) {
        if (d == -1) return 0;

        filterByObs(belief, d);
        if (belief.empty()) {
            cout << "no" << '\n' << flush;
            return 0;
        }

        if (isUniqueCell(belief)) {
            int cid = classCell[belief[0]];
            auto [i, j] = cellCoord[cid];
            cout << "yes " << (i + 1) << ' ' << (j + 1) << '\n' << flush;
            return 0;
        }

        vector<int> actions;
        actions.push_back(0); // left
        actions.push_back(1); // right
        if (d > 0) actions.push_back(2); // step

        vector<EvalRes> evals;
        evals.reserve(actions.size());
        for (int a : actions) evals.push_back(evalAction(belief, a));

        sort(evals.begin(), evals.end(), [&](const EvalRes& A, const EvalRes& B) {
            if (A.worst2 != B.worst2) return A.worst2 < B.worst2;
            if (A.worst1 != B.worst1) return A.worst1 < B.worst1;
            if (A.pref != B.pref) return A.pref < B.pref;
            return A.action < B.action;
        });

        uint64_t hb = hashBelief(belief, d);
        int &cnt = seenBeliefCount[hb];
        int pick = min<int>(cnt, (int)evals.size() - 1);
        // rotate choice a bit if we revisit often
        if (cnt >= 2 && (int)evals.size() > 1) pick = cnt % (int)evals.size();
        cnt++;

        int action = evals[pick].action;

        if (action == 0) cout << "left" << '\n' << flush;
        else if (action == 1) cout << "right" << '\n' << flush;
        else cout << "step" << '\n' << flush;

        belief = applyAction(belief, action);

        if (!(cin >> d)) return 0;
    }

    return 0;
}