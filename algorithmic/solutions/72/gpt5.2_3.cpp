#include <bits/stdc++.h>
using namespace std;

struct Veh {
    bool hor;      // true: horizontal, false: vertical
    int len;       // 2 or 3
    int fixed;     // row if horizontal, col if vertical
};

struct PMove {
    uint8_t id;
    char dir;
};

struct HashTable {
    static constexpr uint32_t EMPTY = 0xFFFFFFFFu;
    vector<uint32_t> keys;
    vector<int> vals;
    size_t sz = 0, cap = 0, mask = 0;

    static inline uint32_t h32(uint32_t x) {
        x ^= x >> 16;
        x *= 0x7feb352du;
        x ^= x >> 15;
        x *= 0x846ca68bu;
        x ^= x >> 16;
        return x;
    }

    void init(size_t expected) {
        cap = 1;
        size_t need = max<size_t>(8, expected * 2);
        while (cap < need) cap <<= 1;
        mask = cap - 1;
        keys.assign(cap, EMPTY);
        vals.assign(cap, -1);
        sz = 0;
    }

    void rehash() {
        size_t oldCap = cap;
        vector<uint32_t> oldKeys = std::move(keys);
        vector<int> oldVals = std::move(vals);

        cap <<= 1;
        mask = cap - 1;
        keys.assign(cap, EMPTY);
        vals.assign(cap, -1);
        sz = 0;

        for (size_t i = 0; i < oldCap; i++) {
            uint32_t k = oldKeys[i];
            if (k == EMPTY) continue;
            put(k, oldVals[i]);
        }
    }

    inline int get(uint32_t key) const {
        size_t i = (size_t)h32(key) & mask;
        while (true) {
            uint32_t k = keys[i];
            if (k == EMPTY) return -1;
            if (k == key) return vals[i];
            i = (i + 1) & mask;
        }
    }

    inline void put(uint32_t key, int val) {
        if ((sz + 1) * 10 >= cap * 7) rehash();
        size_t i = (size_t)h32(key) & mask;
        while (true) {
            uint32_t &k = keys[i];
            if (k == EMPTY) {
                k = key;
                vals[i] = val;
                sz++;
                return;
            }
            // assume key not present
            i = (i + 1) & mask;
        }
    }
};

static inline void decodePos(uint32_t code, int n, int pos[]) {
    for (int i = 1; i <= n; i++) pos[i] = (int)((code >> (3u * (i - 1))) & 7u);
}

static inline void buildOcc(int n, const vector<Veh>& veh, const int pos[], uint8_t occ[36]) {
    memset(occ, 0, 36);
    for (int id = 1; id <= n; id++) {
        int p = pos[id];
        if (id == 1 && p == 6) continue; // red totally out occupies nothing
        const Veh &v = veh[id];
        if (v.hor) {
            int r = v.fixed;
            int x = p;
            for (int k = 0; k < v.len; k++) {
                int c = x + k;
                if ((unsigned)c < 6u) occ[r * 6 + c] = (uint8_t)id;
            }
        } else {
            int c = v.fixed;
            int y = p;
            for (int k = 0; k < v.len; k++) {
                int r = y + k;
                if ((unsigned)r < 6u) occ[r * 6 + c] = (uint8_t)id;
            }
        }
    }
}

static inline void tryMoveAndInsert(
    uint32_t code, int id, int newPos,
    vector<uint32_t>& states, vector<int>& parent, vector<PMove>& pmove,
    HashTable& mp, vector<int>& q, int curIdx, char dir)
{
    uint32_t shift = 3u * (uint32_t)(id - 1);
    uint32_t mask = 7u << shift;
    uint32_t ncode = (code & ~mask) | ((uint32_t)newPos << shift);
    if (mp.get(ncode) != -1) return;
    int idx = (int)states.size();
    mp.put(ncode, idx);
    states.push_back(ncode);
    parent.push_back(curIdx);
    pmove.push_back(PMove{(uint8_t)id, dir});
    q.push_back(idx);
}

static inline void expandState(
    uint32_t code, int n, const vector<Veh>& veh, const int pos[], const uint8_t occ[36],
    vector<uint32_t>& states, vector<int>& parent, vector<PMove>& pmove,
    HashTable& mp, vector<int>& q, int curIdx)
{
    for (int id = 1; id <= n; id++) {
        const Veh &v = veh[id];
        int p = pos[id];
        if (v.hor) {
            int r = v.fixed;

            // Left
            if (p > 0) {
                int cc = p - 1;
                if (occ[r * 6 + cc] == 0) {
                    tryMoveAndInsert(code, id, p - 1, states, parent, pmove, mp, q, curIdx, 'L');
                }
            }

            // Right
            if (id == 1) {
                if (p < 6) {
                    bool ok = true;
                    int front = p + v.len;
                    if (front < 6) {
                        if (occ[r * 6 + front] != 0) ok = false;
                    }
                    if (ok) {
                        tryMoveAndInsert(code, id, p + 1, states, parent, pmove, mp, q, curIdx, 'R');
                    }
                }
            } else {
                int front = p + v.len;
                if (front < 6 && occ[r * 6 + front] == 0) {
                    tryMoveAndInsert(code, id, p + 1, states, parent, pmove, mp, q, curIdx, 'R');
                }
            }
        } else {
            int c = v.fixed;

            // Up
            if (p > 0) {
                int rr = p - 1;
                if (occ[rr * 6 + c] == 0) {
                    tryMoveAndInsert(code, id, p - 1, states, parent, pmove, mp, q, curIdx, 'U');
                }
            }

            // Down
            int back = p + v.len;
            if (back < 6 && occ[back * 6 + c] == 0) {
                tryMoveAndInsert(code, id, p + 1, states, parent, pmove, mp, q, curIdx, 'D');
            }
        }
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int a[6][6];
    int n = 0;
    for (int r = 0; r < 6; r++) {
        for (int c = 0; c < 6; c++) {
            if (!(cin >> a[r][c])) return 0;
            n = max(n, a[r][c]);
        }
    }

    vector<int> minr(n + 1, 6), maxr(n + 1, -1), minc(n + 1, 6), maxc(n + 1, -1), cnt(n + 1, 0);
    for (int r = 0; r < 6; r++) for (int c = 0; c < 6; c++) {
        int id = a[r][c];
        if (id <= 0) continue;
        minr[id] = min(minr[id], r);
        maxr[id] = max(maxr[id], r);
        minc[id] = min(minc[id], c);
        maxc[id] = max(maxc[id], c);
        cnt[id]++;
    }

    vector<Veh> veh(n + 1);
    vector<int> initPos(n + 1, 0);

    for (int id = 1; id <= n; id++) {
        bool hor = (maxr[id] == minr[id]);
        int len = hor ? (maxc[id] - minc[id] + 1) : (maxr[id] - minr[id] + 1);
        veh[id] = Veh{hor, len, hor ? minr[id] : minc[id]};
        initPos[id] = hor ? minc[id] : minr[id];
    }

    uint32_t initCode = 0;
    for (int id = 1; id <= n; id++) initCode |= (uint32_t)initPos[id] << (3u * (uint32_t)(id - 1));

    // Forward BFS from initial (treat red totally out (pos==6) as terminal).
    HashTable mp;
    mp.init(200000);

    vector<uint32_t> states;
    vector<int> parent;
    vector<PMove> pmove;
    vector<int> q;

    states.reserve(200000);
    parent.reserve(200000);
    pmove.reserve(200000);
    q.reserve(200000);

    mp.put(initCode, 0);
    states.push_back(initCode);
    parent.push_back(-1);
    pmove.push_back(PMove{0, '?'});
    q.push_back(0);

    int pos[11];
    uint8_t occ[36];

    for (size_t head = 0; head < q.size(); head++) {
        int curIdx = q[head];
        uint32_t code = states[curIdx];

        decodePos(code, n, pos);
        if (pos[1] == 6) continue; // terminal in forward exploration

        buildOcc(n, veh, pos, occ);
        expandState(code, n, veh, pos, occ, states, parent, pmove, mp, q, curIdx);
    }

    int M = (int)states.size();

    // Reverse BFS from all goal states (red pos == 6)
    vector<int> dist(M, -1);
    vector<int> rq;
    rq.reserve(M);

    for (int i = 0; i < M; i++) {
        if ((states[i] & 7u) == 6u) {
            dist[i] = 0;
            rq.push_back(i);
        }
    }

    for (size_t head = 0; head < rq.size(); head++) {
        int curIdx = rq[head];
        uint32_t code = states[curIdx];

        decodePos(code, n, pos);
        buildOcc(n, veh, pos, occ);

        // Generate neighbors (reversible), and relax
        for (int id = 1; id <= n; id++) {
            const Veh &v = veh[id];
            int p = pos[id];

            auto relax = [&](int newPos) {
                uint32_t shift = 3u * (uint32_t)(id - 1);
                uint32_t mask = 7u << shift;
                uint32_t ncode = (code & ~mask) | ((uint32_t)newPos << shift);
                int j = mp.get(ncode);
                if (j == -1) return;
                if (dist[j] != -1) return;
                dist[j] = dist[curIdx] + 1;
                rq.push_back(j);
            };

            if (v.hor) {
                int r = v.fixed;
                if (p > 0) {
                    int cc = p - 1;
                    if (occ[r * 6 + cc] == 0) relax(p - 1);
                }
                if (id == 1) {
                    if (p < 6) {
                        int front = p + v.len;
                        if (front >= 6 || occ[r * 6 + front] == 0) relax(p + 1);
                    }
                } else {
                    int front = p + v.len;
                    if (front < 6 && occ[r * 6 + front] == 0) relax(p + 1);
                }
            } else {
                int c = v.fixed;
                if (p > 0) {
                    int rr = p - 1;
                    if (occ[rr * 6 + c] == 0) relax(p - 1);
                }
                int back = p + v.len;
                if (back < 6 && occ[back * 6 + c] == 0) relax(p + 1);
            }
        }
    }

    int bestIdx = 0;
    int bestD = -1;
    for (int i = 0; i < M; i++) {
        if (dist[i] > bestD) {
            bestD = dist[i];
            bestIdx = i;
        }
    }
    if (bestD < 0) { // should not happen
        bestD = 0;
        bestIdx = 0;
    }

    vector<PMove> path;
    for (int cur = bestIdx; parent[cur] != -1; cur = parent[cur]) path.push_back(pmove[cur]);
    reverse(path.begin(), path.end());

    cout << bestD << " " << (int)path.size() << "\n";
    for (auto &m : path) {
        cout << (int)m.id << " " << m.dir << "\n";
    }
    return 0;
}